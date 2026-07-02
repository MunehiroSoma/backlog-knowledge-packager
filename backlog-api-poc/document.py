"""
Backlog ドキュメント API ラッパー
"""
import json
from client import BacklogClient


def list_documents(client: BacklogClient, keyword: str = None, offset: int = 0, count: int = 20):
    """
    ドキュメント一覧を取得
    
    Args:
        client: BacklogClient インスタンス
        keyword: 検索キーワード（オプション）
        offset: 取得開始位置
        count: 取得件数（1〜100）
    
    Returns:
        dict: レスポンス JSON
    """
    params = {
        'projectId[]': client.project_id,
        'offset': offset,
        'count': count,
    }
    
    if keyword:
        params['keyword'] = keyword
    
    response = client.get('/api/v2/documents', params=params)
    response.raise_for_status()
    
    return response.json()


def get_document(client: BacklogClient, document_id: str):
    """
    ドキュメント1件を取得
    
    Args:
        client: BacklogClient インスタンス
        document_id: ドキュメント ID（UUID形式）
    
    Returns:
        dict: ドキュメント情報
    """
    response = client.get(f'/api/v2/documents/{document_id}')
    response.raise_for_status()
    
    return response.json()


def create_document(
    client: BacklogClient,
    title: str,
    content: str,
    emoji: str = None,
    parent_id: str = None
):
    """
    ドキュメントを新規作成
    
    Args:
        client: BacklogClient インスタンス
        title: タイトル
        content: 本文（Markdown形式）
        emoji: タイトル横の絵文字（オプション）
        parent_id: 親ドキュメント ID（オプション）
    
    Returns:
        dict: 作成されたドキュメント情報
    """
    payload = {
        'projectId': client.project_id,
        'title': title,
        'content': content,
    }
    
    if emoji:
        payload['emoji'] = emoji
    
    if parent_id:
        payload['parentId'] = parent_id
    
    response = client.post(
        '/api/v2/documents',
        data=payload,
    )
    response.raise_for_status()
    
    return response.json()
