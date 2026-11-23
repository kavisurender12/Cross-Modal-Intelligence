import os
import uuid
import logging
from flask import request, current_app
from flask_jwt_extended import get_jwt_identity

from app.middleware.auth_middleware import require_auth
from app.utils.validators import sanitize_text, allowed_image, is_valid_url
from app.utils.response_helpers import success_response, error_response, risk_level_from_score
from app.models.analysis_model import AnalysisModel
from app.ai_models import fake_news_model, phishing_model, fraud_model, cross_modal_engine
from app.ai_models.ocr_service import extract_text as ocr_extract

logger = logging.getLogger(__name__)

RECOMMENDATIONS = {
    'fake_news': [
        'Cross-check with established, reputable news sources.',
        'Look for original sourcing and author credentials.',
        'Be cautious about sharing unverified content.',
        'Check fact-checking platforms like Snopes, PolitiFact, or FactCheck.org.'
    ],
    'phishing': [
        'Do not click on suspicious links.',
        'Verify the sender through an independent, official channel.',
        'Never share OTPs, passwords, or bank credentials.',
        'Report phishing attempts to your bank or relevant authority.'
    ],
    'fraud': [
        'Do not pay any advance fees or registration charges.',
        'Legitimate jobs/schemes do not ask for upfront payments.',
        'Verify offers through official company websites or government portals.',
        'Report fraud to cybercrime authorities (cybercrime.gov.in in India).'
    ]
}


def _safe_recommendation(module: str, risk_score: float) -> list:
    recs = RECOMMENDATIONS.get(module, [])
    if risk_score >= 65:
        return recs
    elif risk_score >= 35:
        return recs[:2] + ['Exercise caution and verify independently.']
    return ['No specific action required, but always stay vigilant.']


def _normalize_url(url: str) -> str:
    """Ensure URL has a scheme for validation and analysis."""
    url = url.strip()
    if url and not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url


class DetectController:

    @staticmethod
    @require_auth
    def fake_news():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        text = sanitize_text(data.get('text', ''))
        url = sanitize_text(data.get('url', ''), max_length=500)

        if not text and not url:
            return error_response('Please provide article text or a URL', 400)

        # For URL mode: analyze the URL string as text (live fetching not supported)
        input_for_analysis = text if text else url
        input_content = input_for_analysis

        try:
            result = fake_news_model.analyze(input_for_analysis)
        except Exception as e:
            logger.error(f"Fake news analysis error: {e}")
            return error_response('Analysis engine error. Please try again.', 500)

        risk_level = risk_level_from_score(result['risk_score'])
        recommendations = _safe_recommendation('fake_news', result['risk_score'])

        try:
            analysis_id = AnalysisModel.save_analysis(user_id, {
                'input_type': 'url' if (url and not text) else 'text',
                'input_content': input_content[:500],
                'detection_module': 'fake_news',
                'prediction': result['label'],
                'risk_score': result['risk_score'],
                'risk_level': risk_level,
                'confidence': result.get('confidence'),
                'suspicious_indicators': result.get('suspicious_indicators', []),
                'explanation': result.get('note', ''),
                'recommendations': recommendations
            })
        except Exception as e:
            logger.error(f"Save analysis error: {e}")
            analysis_id = None

        return success_response(data={
            'analysis_id': analysis_id,
            'prediction': result['label'],
            'risk_score': result['risk_score'],
            'risk_level': risk_level,
            'confidence': result.get('confidence'),
            'suspicious_indicators': result.get('suspicious_indicators', []),
            'credibility_markers': result.get('credibility_markers', []),
            'explanation': result.get('note', ''),
            'method': result.get('method'),
            'recommendations': recommendations
        })

    @staticmethod
    @require_auth
    def phishing():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        text = sanitize_text(data.get('text', ''))
        url = sanitize_text(data.get('url', ''), max_length=500)

        if not text and not url:
            return error_response('Please provide email/SMS text or a URL', 400)

        results = {}

        if url:
            # Normalize URL — prepend scheme if missing
            url_normalized = _normalize_url(url)
            try:
                results['url'] = phishing_model.analyze_url(url_normalized)
            except Exception as e:
                logger.error(f"URL analysis error: {e}")
                results['url'] = {'risk_score': 0, 'label': 'Error', 'suspicious_indicators': []}

        if text:
            try:
                results['text'] = phishing_model.analyze_text(text)
            except Exception as e:
                logger.error(f"Text phishing analysis error: {e}")
                results['text'] = {'risk_score': 0, 'label': 'Error', 'suspicious_indicators': []}

        all_scores = [r['risk_score'] for r in results.values() if r.get('risk_score') is not None]
        if not all_scores:
            return error_response('Analysis failed for all provided inputs', 500)

        risk_score = max(all_scores)
        all_indicators = []
        for r in results.values():
            all_indicators.extend(r.get('suspicious_indicators', []))

        risk_level = risk_level_from_score(risk_score)
        label = 'Likely Phishing' if risk_score >= 65 else ('Suspicious' if risk_score >= 35 else 'Likely Safe')
        recommendations = _safe_recommendation('phishing', risk_score)
        confidence = results.get('url', results.get('text', {})).get('confidence')

        input_content = url or text[:200]
        try:
            analysis_id = AnalysisModel.save_analysis(user_id, {
                'input_type': 'url' if url else 'text',
                'input_content': input_content[:500],
                'detection_module': 'phishing',
                'prediction': label,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'confidence': confidence,
                'suspicious_indicators': list(dict.fromkeys(all_indicators)),
                'explanation': 'Phishing analysis combining URL features and text patterns.',
                'recommendations': recommendations,
                'modality_results': results
            })
        except Exception as e:
            logger.error(f"Save analysis error: {e}")
            analysis_id = None

        return success_response(data={
            'analysis_id': analysis_id,
            'prediction': label,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'phishing_probability': risk_score,
            'confidence': confidence,
            'suspicious_indicators': list(dict.fromkeys(all_indicators)),
            'url_features': results.get('url', {}).get('url_features', {}),
            'explanation': 'Phishing analysis combining URL features and text patterns.',
            'note': results.get('url', results.get('text', {})).get('note', ''),
            'recommendations': recommendations,
            'modality_results': {k: {kk: vv for kk, vv in v.items() if kk != 'url_features'} for k, v in results.items()}
        })

    @staticmethod
    @require_auth
    def digital_fraud():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        text = sanitize_text(data.get('text', ''))

        if not text:
            return error_response('Please provide text to analyse', 400)

        try:
            result = fraud_model.analyze(text)
        except Exception as e:
            logger.error(f"Fraud analysis error: {e}")
            return error_response('Analysis engine error. Please try again.', 500)

        risk_level = risk_level_from_score(result['risk_score'])
        recommendations = _safe_recommendation('fraud', result['risk_score'])

        try:
            analysis_id = AnalysisModel.save_analysis(user_id, {
                'input_type': 'text',
                'input_content': text[:500],
                'detection_module': 'digital_fraud',
                'prediction': result['label'],
                'risk_score': result['risk_score'],
                'risk_level': risk_level,
                'confidence': result.get('confidence'),
                'fraud_category': result.get('fraud_category'),
                'suspicious_indicators': result.get('suspicious_indicators', []),
                'explanation': result.get('note', ''),
                'recommendations': recommendations
            })
        except Exception as e:
            logger.error(f"Save analysis error: {e}")
            analysis_id = None

        return success_response(data={
            'analysis_id': analysis_id,
            'prediction': result['label'],
            'risk_score': result['risk_score'],
            'risk_level': risk_level,
            'fraud_probability': result.get('fraud_probability'),
            'fraud_category': result.get('fraud_category'),
            'confidence': result.get('confidence'),
            'suspicious_indicators': result.get('suspicious_indicators', []),
            'explanation': result.get('note', ''),
            'method': result.get('method'),
            'recommendations': recommendations
        })

    @staticmethod
    @require_auth
    def cross_modal():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        text = sanitize_text(data.get('text', ''))
        url = sanitize_text(data.get('url', ''), max_length=500)
        hint = data.get('detection_hint')

        if not text and not url:
            return error_response('Please provide text and/or a URL for cross-modal analysis', 400)

        # Normalize URL
        url_norm = _normalize_url(url) if url else None

        try:
            result = cross_modal_engine.analyze(
                text=text or None,
                url=url_norm,
                detection_hint=hint if hint in ['fake_news', 'phishing', 'fraud'] else None
            )
        except Exception as e:
            logger.error(f"Cross-modal analysis error: {e}")
            return error_response('Analysis engine error. Please try again.', 500)

        try:
            analysis_id = AnalysisModel.save_analysis(user_id, {
                'input_type': 'cross_modal',
                'input_content': (text or url)[:500],
                'detection_module': 'cross_modal',
                'prediction': result['final_label'],
                'risk_score': result['risk_score'],
                'risk_level': result['risk_level'],
                'suspicious_indicators': result['suspicious_indicators'],
                'explanation': result['explanation'],
                'recommendations': result.get('recommendations', []),
                'modality_results': result['modality_results']
            })
        except Exception as e:
            logger.error(f"Save analysis error: {e}")
            analysis_id = None

        return success_response(data={
            'analysis_id': analysis_id,
            **result
        })

    @staticmethod
    @require_auth
    def image_analysis():
        user_id = get_jwt_identity()

        if 'image' not in request.files:
            return error_response('No image file provided', 400)

        file = request.files['image']
        if not file or not file.filename:
            return error_response('No file selected', 400)
        if not allowed_image(file.filename):
            return error_response('File type not allowed. Use JPG, JPEG, PNG, or WEBP', 400)

        # Save file to absolute upload folder
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)

        try:
            os.makedirs(upload_folder, exist_ok=True)
            file.save(filepath)
        except Exception as e:
            logger.error(f"File save error: {e}")
            return error_response(f'Could not save uploaded file: {e}', 500)

        try:
            # Step 1: OCR extraction
            ocr_result = ocr_extract(filepath)
            extracted_text = (ocr_result.get('text', '') or '').strip()
            ocr_urls = ocr_result.get('urls', [])

            if not extracted_text and not ocr_urls:
                try:
                    analysis_id = AnalysisModel.save_analysis(user_id, {
                        'input_type': 'image',
                        'input_content': f'[image: {filename}]',
                        'detection_module': 'image',
                        'prediction': 'No text extracted',
                        'risk_score': 0,
                        'risk_level': 'Low',
                        'extracted_text': '',
                        'explanation': ocr_result.get('error', 'No readable text found in the image.'),
                        'recommendations': ['Try uploading a clearer image with visible text.']
                    })
                except Exception:
                    analysis_id = None

                return success_response(data={
                    'analysis_id': analysis_id,
                    'ocr': ocr_result,
                    'extracted_text': '',
                    'prediction': 'No text extracted',
                    'risk_score': 0,
                    'risk_level': 'Low',
                    'suspicious_indicators': [],
                    'recommendations': ['Try uploading a clearer image with visible text.'],
                    'message': 'No readable text was found in the image.'
                })

            # Step 2: Cross-modal analysis
            # Pass extracted_text ONLY as extracted_text (not text) to avoid double-counting
            primary_url = ocr_urls[0] if ocr_urls else None
            try:
                result = cross_modal_engine.analyze(
                    text=None,                        # no separate user-submitted text
                    url=primary_url,
                    extracted_text=extracted_text,    # OCR text goes here only
                )
            except Exception as e:
                logger.error(f"Cross-modal analysis on image error: {e}")
                result = {
                    'final_label': 'Analysis Error',
                    'risk_score': 0,
                    'risk_level': 'Low',
                    'suspicious_indicators': [],
                    'explanation': str(e),
                    'recommendations': [],
                    'modality_results': {},
                    'is_cross_modal': False,
                    'fusion_note': ''
                }

            try:
                analysis_id = AnalysisModel.save_analysis(user_id, {
                    'input_type': 'image',
                    'input_content': f'[image: {filename}]',
                    'detection_module': 'image',
                    'prediction': result['final_label'],
                    'risk_score': result['risk_score'],
                    'risk_level': result['risk_level'],
                    'extracted_text': extracted_text[:1000],
                    'suspicious_indicators': result['suspicious_indicators'],
                    'explanation': result['explanation'],
                    'recommendations': result.get('recommendations', []),
                    'modality_results': result['modality_results']
                })
            except Exception as e:
                logger.error(f"Save analysis error: {e}")
                analysis_id = None

            return success_response(data={
                'analysis_id': analysis_id,
                'ocr': ocr_result,
                'extracted_text': extracted_text,
                'extracted_urls': ocr_urls,
                **result
            })

        finally:
            # Always clean up the uploaded file
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
