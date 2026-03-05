class LoadImageError(Exception):
    """Raised when loading (pulling) a container image fails."""

    def __init__(self, image: str, code: int, stderr: str):
        self.image = image
        self.code = code
        self.stderr = stderr
        super().__init__(f"Failed to load image {image} with code {code}: {stderr}")
