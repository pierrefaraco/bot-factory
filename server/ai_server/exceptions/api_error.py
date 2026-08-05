class ApiError(Exception):
    """Generic API error handler"""

    DEFAULT_STATUS_CODE = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)

        if status_code is not None:
            self.status_code = status_code
        else:
            self.status_code = ApiError.DEFAULT_STATUS_CODE

        self.data = {}
        self.data["message"] = ""

        if payload is not None:
            self.data["payload"] = ""

        if isinstance(message, str) and message.strip():
            self.data["message"] = message
        elif isinstance(message, Exception):
            self.data["message"] = "Exception: " + str(message)
        elif message is not None:
            self.message = str(message)

        self.payload = payload

    def __str__(self):
        return self.data["message"]

    def to_dict(self):
        return self.data
