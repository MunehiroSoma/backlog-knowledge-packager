"""
Backlog API クライアント基盤
"""
import os
from urllib.parse import urljoin
from dotenv import load_dotenv
import requests

# .env ファイルを読み込む
load_dotenv()


class BacklogClient:
    """Backlog REST API クライアント"""
    
    def __init__(self):
        self.space_key = os.getenv('BACKLOG_SPACE_KEY')
        self.api_key = os.getenv('BACKLOG_API_KEY')
        self.project_id = os.getenv('BACKLOG_PROJECT_ID')
        
        if not self.space_key or not self.api_key:
            raise ValueError('BACKLOG_SPACE_KEY and BACKLOG_API_KEY must be set in .env')
        
        # ベースURLを構成
        self.base_url = f'https://{self.space_key}.backlog.com'
        
        # リクエストセッションを構成（APIキーをクエリパラメータに追加）
        self.session = requests.Session()
        self.session.params = {'apiKey': self.api_key}
    
    def get(self, endpoint, **kwargs):
        """GET リクエスト"""
        url = urljoin(self.base_url, endpoint)
        return self.session.get(url, **kwargs)
    
    def post(self, endpoint, **kwargs):
        """POST リクエスト"""
        url = urljoin(self.base_url, endpoint)
        return self.session.post(url, **kwargs)
    
    def delete(self, endpoint, **kwargs):
        """DELETE リクエスト"""
        url = urljoin(self.base_url, endpoint)
        return self.session.delete(url, **kwargs)
    
    def close(self):
        """セッションをクローズ"""
        self.session.close()
