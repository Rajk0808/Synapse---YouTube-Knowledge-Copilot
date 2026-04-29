import tiktoken

#get encoding for a specific model
encoding = tiktoken.encoding_for_model('gpt-4')

#tokens = encoding.encode('Hello, i am raj.')

# print(tokens) -> [9906, 11, 602, 1097, 92528, 13]

#tokens = [9906, 11, 602, 1097, 92528, 13]

# print(encoding.decode([9906, 11, 602, 1097, 92528, 13])) -> Hello, i am raj.



tokens = encoding.encode('Unhappiness')

# print([encoding.decode_single_token_bytes(token).decode('utf-8') for token in tokens]) -> ['Un', 'h', 'appiness']

from pypdf import PdfReader
reader = PdfReader("Phase-01/test.pdf")
text = [reader.pages[i].extract_text() for i in range(4)]

tokens = [encoding.encode(t) for t in text]
actual_tokens = []
for token in tokens:
    actual_tokens += token
# print(len(actual_tokens)) -> 1871
# 30.00 per 1 million input tokens
# which would cost of around 
# it cost of aroud 0.05613 dollars.