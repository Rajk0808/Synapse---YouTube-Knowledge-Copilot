class CustomException(Exception):
    def __init__(self,message):
        self.message = message
        super().__init__()
    def __str__(self):
        print(self.message)