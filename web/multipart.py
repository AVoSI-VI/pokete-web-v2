"""Read one uploaded file from a multipart form body."""


class UploadError(ValueError):
    pass


def _boundary(content_type: str) -> bytes:
    for piece in content_type.split(";"):
        item = piece.strip()
        if item.startswith("boundary="):
            value = item.split("=", 1)[1].strip().strip('"')
            if value:
                return b"--" + value.encode("utf-8")
    raise UploadError("missing upload boundary")


def _filename(headers: str) -> str | None:
    for line in headers.split("\r\n"):
        if "filename=" not in line.lower():
            continue
        _, _, rest = line.partition("filename=")
        rest = rest.strip()
        if rest.startswith('"'):
            return rest.split('"', 2)[1]
        return rest.split(";", 1)[0].strip()
    return None


def read_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    if "multipart/form-data" not in content_type:
        raise UploadError("expected a file upload")
    boundary = _boundary(content_type)
    for chunk in body.split(boundary):
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]
        header_blob, sep, data = chunk.partition(b"\r\n\r\n")
        if not sep:
            continue
        name = _filename(header_blob.decode("utf-8", "replace"))
        if name:
            return name, data
    raise UploadError("no file was uploaded")
