class ChapterNameAlreadyExist(Exception):
    def __init__(self):
        self.message = "this chapter name already exist"

    def __str__(self):
        return self.message
