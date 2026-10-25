class AppError(Exception):
    """An expected error that should reach the client as a clean JSON message.

    Kept free of FastAPI imports so services can raise it and stay unit-testable.
    main.py registers a handler that turns it into {"detail": message}.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
