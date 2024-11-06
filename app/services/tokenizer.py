# app/services/tokenizer.py
import tiktoken

class TokenizerService:
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text):
        """
        テキストのトークン数を計算
        Args:
            text (str): 入力テキスト
        Returns:
            int: トークン数
        """
        tokens = self.tokenizer.encode(text)
        return len(tokens)

    def validate_input_length(self, text, max_length):
        """
        入力テキストの長さを検証
        Args:
            text (str): 入力テキスト
            max_length (int): 最大トークン数
        Returns:
            bool: 制限内ならTrue
        """
        return self.count_tokens(text) <= max_length