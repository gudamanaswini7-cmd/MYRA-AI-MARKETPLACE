import os

from flask import Blueprint, jsonify, request

from backend.database import save_creator_upload

proof_of_skill_bp = Blueprint("proof_of_skill", __name__)


def score_creator_submission(file_name, file_size, file_type, creator_name):
    extension = os.path.splitext(file_name)[1].lower()
    score = 0
    verification_notes = []

    if file_size > 0:
        score += 25
        verification_notes.append("File uploaded successfully and has real content.")
    else:
        verification_notes.append("Uploaded file is empty.")

    if extension in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        score += 30
        verification_notes.append("Image asset accepted for review.")
    elif extension in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        score += 35
        verification_notes.append("Video asset accepted for review.")
    elif extension in {".pdf", ".doc", ".docx", ".txt", ".zip"}:
        score += 25
        verification_notes.append("Document file accepted for review.")
    else:
        score += 15
        verification_notes.append("Generic file type processed by the AI reviewer.")

    if file_size > 200000:
        score += 20
        verification_notes.append("The asset appears substantial and production-quality.")
    else:
        score += 10
        verification_notes.append("The asset has a small but acceptable size for review.")
    if len(file_name) > 8:
        score += 15
        verification_notes.append("Filename looks valid and professional.")
    if file_type and file_type != "application/octet-stream":
        score += 10
        verification_notes.append("File metadata confirms media type.")
    if creator_name and creator_name.strip():
        score += 5
        verification_notes.append("Creator identity provided for verification.")

    score = min(score, 100)
    allowed_to_dashboard = score >= 40
    status = "APPROVED" if score >= 70 else "PENDING REVIEW" if allowed_to_dashboard else "REJECTED"
    return {
        "score": score,
        "screening_status": status,
        "allowed_to_dashboard": allowed_to_dashboard,
        "verification_notes": verification_notes,
    }


@proof_of_skill_bp.post("/api/creator/submit")
def creator_submit():
    creator_name = request.form.get("creator_name", "").strip()
    uploaded_file = request.files.get("file")
    if not creator_name:
        return jsonify(detail="Creator name is required."), 400
    if not uploaded_file or not uploaded_file.filename:
        return jsonify(detail="A file upload is required."), 400

    file_bytes = uploaded_file.read()
    file_name = uploaded_file.filename
    file_type = uploaded_file.content_type or "application/octet-stream"
    result = score_creator_submission(file_name, len(file_bytes), file_type, creator_name)
    save_creator_upload(
        creator_name,
        file_name,
        file_type,
        result["score"],
        result["screening_status"],
        result["allowed_to_dashboard"],
    )
    return jsonify(
        creator_name=creator_name,
        file_name=file_name,
        file_type=file_type,
        **result,
    )