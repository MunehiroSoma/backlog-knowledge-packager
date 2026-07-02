"""
Backlog ドキュメント API 動作確認スクリプト
"""
import json
from client import BacklogClient
from document import list_documents, get_document, create_document


def main():
    """メイン処理"""
    client = None
    try:
        # クライアントを初期化
        client = BacklogClient()
        print(f'✓ Backlog スペース接続: {client.space_key}')
        print(f'✓ プロジェクト ID: {client.project_id}')
        print()
        
        # 1. ドキュメント一覧を取得
        print('【操作1】ドキュメント一覧を取得')
        print('-' * 50)
        documents = list_documents(client, count=5)
        print(f'取得件数: {len(documents)}')
        for doc in documents:
            print(f'  - ID: {doc["id"]}, Title: {doc["name"]}')
        print()
        
        # 2. 最初のドキュメントを詳細取得（存在する場合）
        if documents:
            print('【操作2】最初のドキュメントを詳細取得')
            print('-' * 50)
            first_doc_id = documents[0]['id']
            detail = get_document(client, first_doc_id)
            print(f'ID: {detail["id"]}')
            print(f'Title: {detail["name"]}')
            print(f'Content (最初の100文字):')
            print(f'  {detail["content"][:100]}...')
            print()
        else:
            print('【操作2】スキップ（ドキュメントがありません）')
            print()
        
        # 3. 新しいドキュメントを作成（テスト用）
        print('【操作3】新しいドキュメントを作成')
        print('-' * 50)
        new_doc = create_document(
            client,
            title='テストドキュメント',
            content='これはPythonスクリプトから作成したテストドキュメントです。',
            emoji='🧪'
        )
        print(f'✓ 作成成功')
        print(f'  ID: {new_doc["id"]}')
        print(f'  Title: {new_doc["name"]}')
        print()
        
        print('✓ 全ての操作が完了しました')
        
    except ValueError as e:
        print(f'✗ エラー: {e}')
        print('  .env ファイルで BACKLOG_SPACE_KEY, BACKLOG_API_KEY を設定してください')
    except Exception as e:
        print(f'✗ エラーが発生しました: {e}')
    finally:
        if client is not None:
            client.close()


if __name__ == '__main__':
    main()
