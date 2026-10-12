"""Cloudinary configuration and signed upload validation for shared Reels media."""
import hashlib
import mimetypes
import os
import re
import time
import uuid
from urllib.parse import quote, unquote, urlparse, urlunparse
from urllib.request import Request, urlopen


def cloudinary_settings():
    return {
        "cloud_name": os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip(),
        "api_key": os.environ.get("CLOUDINARY_API_KEY", "").strip(),
        "api_secret": os.environ.get("CLOUDINARY_API_SECRET", "").strip(),
    }


def cloudinary_configured():
    return all(cloudinary_settings().values())


def create_upload_signature(filename, allowed_extensions, image_extensions, audio_extensions, file_extensions):
    settings = cloudinary_settings()
    if not all(settings.values()):
        raise RuntimeError("Configure CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET.")

    extension = os.path.splitext(filename)[1].lower()
    if extension not in allowed_extensions:
        raise ValueError("This file type is not supported.")
    resource_type = (
        "image" if extension in image_extensions else
        "video" if extension in audio_extensions or extension not in file_extensions else
        "raw"
    )
    if extension in {".mp4", ".webm", ".mov"}:
        resource_type = "video"

    timestamp = int(time.time())
    public_id = f"myra/reels/{uuid.uuid4().hex}"
    params = {
        "public_id": public_id,
        "timestamp": timestamp,
    }
    signed_params = "&".join(f"{key}={params[key]}" for key in sorted(params))
    signature = hashlib.sha1(f"{signed_params}{settings['api_secret']}".encode("utf-8")).hexdigest()
    return {
        **params,
        "signature": signature,
        "api_key": settings["api_key"],
        "cloud_name": settings["cloud_name"],
        "resource_type": resource_type,
        "upload_url": f"https://api.cloudinary.com/v1_1/{settings['cloud_name']}/{resource_type}/upload",
    }


def validate_cloudinary_asset(asset, original_filename):
    if not isinstance(asset, dict):
        raise ValueError("The uploaded media response is invalid.")

    settings = cloudinary_settings()
    public_id = str(asset.get("public_id") or "")
    resource_type = str(asset.get("resource_type") or "")
    secure_url = str(asset.get("secure_url") or "")
    original_filename = os.path.basename(str(original_filename or ""))
    file_format = str(asset.get("format") or "").lower()

    if not re.fullmatch(r"myra/reels/[a-f0-9]{32}", public_id):
        raise ValueError("The uploaded asset does not belong to the MYRA Reels folder.")
    if not original_filename or resource_type not in {"image", "video", "raw"}:
        raise ValueError("The uploaded media metadata is incomplete.")
    parsed = urlparse(secure_url)
    if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
        raise ValueError("The uploaded media URL is not a trusted Cloudinary URL.")

    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    if (
        len(path_parts) < 6
        or path_parts[0] != settings["cloud_name"]
        or path_parts[1] != resource_type
        or path_parts[2] != "upload"
        or path_parts[-3] != "myra"
        or path_parts[-2] != "reels"
        or not path_parts[-1].startswith(public_id.rsplit("/", 1)[-1] + ".")
    ):
        raise ValueError("The Cloudinary URL does not match the signed upload.")
    if not re.fullmatch(r"[a-z0-9]{1,12}", file_format):
        raise ValueError("The uploaded media format is invalid.")

    return {
        "public_id": public_id,
        "resource_type": resource_type,
        "secure_url": secure_url,
        "original_filename": original_filename,
        "format": file_format,
    }


def cloudinary_delivery_url(asset, media_kind):
    """Deliver uploaded videos in a browser-friendly H.264/AAC MP4 format."""
    if media_kind != "video":
        return asset["secure_url"]

    parsed = urlparse(asset["secure_url"])
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    upload_index = path_parts.index("upload")
    suffix = path_parts[upload_index + 1:]
    suffix[-1] = f"{asset['public_id'].rsplit('/', 1)[-1]}.mp4"
    encoded_suffix = "/".join(quote(part, safe="/,._-") for part in suffix)
    delivery_path = (
        f"/{path_parts[0]}/video/upload/f_mp4,vc_h264,ac_aac/{encoded_suffix}"
    )
    return urlunparse(("https", "res.cloudinary.com", delivery_path, "", "", ""))


def upload_local_media(path, signature):
    """Upload one existing local reel asset to Cloudinary during data migration."""
    boundary = f"----MYRA{uuid.uuid4().hex}"
    fields = {
        "api_key": signature["api_key"],
        "timestamp": str(signature["timestamp"]),
        "signature": signature["signature"],
        "public_id": signature["public_id"],
    }
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode()
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    request = Request(
        signature["upload_url"],
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(request, timeout=180) as response:
        import json

        result = json.loads(response.read().decode("utf-8"))
    return result
