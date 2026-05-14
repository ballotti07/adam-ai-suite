import re

EMOJI_PATTERN = re.compile(
    "["
    u"\U0001F600-\U0001F64F" 
    u"\U0001F300-\U0001F5FF" 
    u"\U0001F680-\U0001F6FF" 
    u"\U0001F700-\U0001F77F" 
    u"\U0001F780-\U0001F7FF" 
    u"\U0001F800-\U0001F8FF" 
    u"\U0001F900-\U0001F9FF" 
    u"\U0001FA00-\U0001FA6F" 
    u"\U0001FA70-\U0001FAFF" 
    u"\U00002702-\U000027B0" 
    u"\U000024C2-\U0001F251" 
    "]+", flags=re.UNICODE
)
MULTI_DOT_PATTERN = re.compile(r'\.{2,}')
CODE_BLOCK_PATTERN = re.compile(r'```.*?```', flags=re.DOTALL)

def remove_emojis(text):
    return EMOJI_PATTERN.sub(r'', text)

def remove_multiple_dots(text):
    return MULTI_DOT_PATTERN.sub('.', text)

def remove_code_blocks(text):
    return CODE_BLOCK_PATTERN.sub('', text)

def find_code_blocks(text):
    return [[match.start(), match.end() - 1] for match in CODE_BLOCK_PATTERN.finditer(text)]