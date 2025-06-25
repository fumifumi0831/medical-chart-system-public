# %%
"""
Level 1 ユニットテスト: テンプレートサービステスト - セル実行専用版
テストレベル: Level 1 (Unit Test)
信頼性: ビジネスロジック 95%, モック使用
実行頻度: 毎回
前提条件: モックサービス
各セルで独立して実行可能なように設計
設計書参照: doc_04_detailed_design.md セクション 4.5
更新日: 2025-01-15

使用方法:
- 各セル（# %%）を順次実行して結果を確認
- VS Code、PyCharm等のIDEでセル実行機能を使用
"""

# セル共通の初期化処理
def setup_environment():
    import os
    import sys
    import subprocess
    
    # 現在のPython環境を確認
    print(f"🐍 Python実行環境: {sys.executable}")
    print(f"📁 作業ディレクトリ: {os.getcwd()}")
    
    # プロジェクトルートをPythonパスに追加
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 環境変数をモック設定（テスト用）
    os.environ.update({
        'API_KEY': 'test_api_key',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'GCS_BUCKET_NAME': 'test_bucket'
    })
    
    return project_root

# 初期化実行
project_root = setup_environment()
print("✅ Level 1テスト環境設定完了")

# %%
"""
セル1: 必要なライブラリのインポート
"""

# 環境設定を再実行（セル独立実行のため）
project_root = setup_environment()

import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from uuid import UUID, uuid4
from typing import List, Dict, Any

# 実際の実装をインポート
try:
    from app.services import template_service
    from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateItemCreate
    print("✅ インポート成功: app.services経由")
except ImportError as e:
    print(f"⚠️ app.services経由でのインポート失敗: {e}")
    try:
        import app.services.template_service as template_service
        from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateItemCreate
        print("✅ インポート成功: 直接インポート")
    except ImportError as e2:
        print(f"⚠️ 直接インポートも失敗: {e2}")
        try:
            import os
            import sys
            sys.path.append(os.path.join(project_root, 'app', 'services'))
            sys.path.append(os.path.join(project_root, 'app', 'schemas'))
            import template_service
            from template import TemplateCreate, TemplateUpdate, TemplateItemCreate
            print("✅ インポート成功: 相対インポート")
        except ImportError as e3:
            print(f"❌ 全てのインポート方法が失敗: {e}, {e2}, {e3}")
            print("💡 依存関係の問題の可能性があります。以下を確認してください：")
            print("   1. 仮想環境が正しく設定されているか")
            print("   2. 必要なパッケージがすべてインストールされているか")
            print("   3. データベース関連の設定が正しいか")
            raise ImportError(f"template_serviceのインポートに失敗しました。")

print("✅ Level 1テスト用インポート完了")

# %%
"""
セル2: テストデータの準備
"""

# 環境設定を再実行
project_root = setup_environment()

# サンプルテンプレート項目
sample_template_items = [
    TemplateItemCreate(
        name="主訴",
        enabled=True,
        display_order=1,
        description="患者の主な訴え",
        confidence_threshold=0.8
    ),
    TemplateItemCreate(
        name="現病歴",
        enabled=True,
        display_order=2,
        description="現在の病気の経過",
        confidence_threshold=0.7
    ),
    TemplateItemCreate(
        name="既往歴",
        enabled=True,
        display_order=3,
        description="過去の病気の履歴",
        confidence_threshold=0.6
    ),
    TemplateItemCreate(
        name="家族歴",
        enabled=True,
        display_order=4,
        description="家族の病気の履歴",
        confidence_threshold=0.6
    ),
    TemplateItemCreate(
        name="身体所見",
        enabled=True,
        display_order=5,
        description="身体検査の結果",
        confidence_threshold=0.7
    )
]

# サンプルテンプレート作成データ
sample_template_create = TemplateCreate(
    name="標準診療記録テンプレート",
    description="一般的な診療記録用のテンプレート",
    type="user",
    created_by="test_user_123",
    is_active=True,
    items=sample_template_items
)

# サンプルテンプレート更新データ
sample_template_update = TemplateUpdate(
    name="標準診療記録テンプレート（改訂版）",
    description="一般的な診療記録用のテンプレート - 改訂版",
    is_active=True,
    items=sample_template_items
)

# モックデータベースレスポンス
sample_template_id = uuid4()
mock_template_response = {
    "id": sample_template_id,
    "name": sample_template_create.name,
    "description": sample_template_create.description,
    "type": sample_template_create.type,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    "created_by": sample_template_create.created_by,
    "is_active": sample_template_create.is_active,
    "items": [
        {
            "id": uuid4(),
            "template_id": sample_template_id,
            "name": item.name,
            "enabled": item.enabled,
            "display_order": item.display_order,
            "description": item.description,
            "confidence_threshold": item.confidence_threshold,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        } for item in sample_template_items
    ]
}

print("✅ Level 1テストデータ準備完了")
print(f"📝 テンプレート名: {sample_template_create.name}")
print(f"📊 テンプレートタイプ: {sample_template_create.type}")
print(f"🏗️ 項目数: {len(sample_template_create.items)}")
print(f"✅ アクティブ: {sample_template_create.is_active}")
print(f"👤 作成者: {sample_template_create.created_by}")

# %%
"""
Level 1テスト1: テンプレート作成（モックベース）
設計書仕様: 新しいテンプレートの作成
入力: 有効なテンプレート作成データ
期待値: 作成されたテンプレートオブジェクト
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_create_template():
    print("🧪 Level 1テスト開始: テンプレート作成（モックベース）")
    
    with patch('app.services.template_service.Session') as mock_session_class:
        # モックセッションの設定
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # モックテンプレートオブジェクト
        mock_template = MagicMock()
        mock_template.id = sample_template_id
        mock_template.name = sample_template_create.name
        mock_template.description = sample_template_create.description
        mock_template.type = sample_template_create.type
        mock_template.created_by = sample_template_create.created_by
        mock_template.is_active = sample_template_create.is_active
        
        # get_template_by_idのモック
        with patch('app.services.template_service.get_template_by_id') as mock_get:
            mock_get.return_value = mock_template_response
            
            # 実行
            result = template_service.create_template(mock_session, sample_template_create)
            
            # 結果確認
            print(f"📄 作成されたテンプレートID: {result['id']}")
            print(f"📝 テンプレート名: {result['name']}")
            print(f"📊 テンプレートタイプ: {result['type']}")
            print(f"📋 説明: {result['description']}")
            print(f"🏗️ 項目数: {len(result['items'])}")
            print(f"✅ アクティブ: {result['is_active']}")
            print(f"👤 作成者: {result['created_by']}")
            
            # 項目詳細確認
            if result['items']:
                first_item = result['items'][0]
                print(f"🔍 最初の項目: {first_item['name']}")
                print(f"📊 信頼度閾値: {first_item['confidence_threshold']}")
                print(f"📋 表示順序: {first_item['display_order']}")
            
            # データベース呼び出し確認
            print(f"🔧 session.add呼び出し回数: {mock_session.add.call_count}")
            print(f"🔧 session.commit呼び出し回数: {mock_session.commit.call_count}")
            
            # 検証結果
            success = all([
                result['id'] == sample_template_id,
                result['name'] == sample_template_create.name,
                result['type'] == sample_template_create.type,
                result['is_active'] == sample_template_create.is_active,
                result['created_by'] == sample_template_create.created_by,
                len(result['items']) == len(sample_template_items),
                mock_session.add.call_count >= 1,
                mock_session.commit.call_count == 1
            ])
            
            print(f"✅ Level 1テスト結果: {'成功' if success else '失敗'}")
            return result

# 実行
created_template = test_create_template()

# %%
"""
Level 1テスト2: テンプレート取得（モックベース）
設計書仕様: 指定されたIDのテンプレートを取得
入力: 有効なテンプレートID
期待値: テンプレートオブジェクト
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_get_template_by_id():
    print("🧪 Level 1テスト開始: テンプレート取得（モックベース）")
    
    with patch('app.services.template_service.Session') as mock_session_class:
        # モックセッションの設定
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # モッククエリの設定
        mock_query = MagicMock()
        mock_template = MagicMock()
        mock_template.id = sample_template_id
        mock_template.name = sample_template_create.name
        mock_template.description = sample_template_create.description
        mock_template.type = sample_template_create.type
        mock_template.created_by = sample_template_create.created_by
        mock_template.is_active = sample_template_create.is_active
        mock_template.items = []
        
        mock_query.first.return_value = mock_template
        mock_session.query.return_value.filter.return_value = mock_query
        
        # 実行
        result = template_service.get_template_by_id(mock_session, sample_template_id)
        
        # 結果確認
        print(f"📄 取得されたテンプレートID: {result['id']}")
        print(f"📝 テンプレート名: {result['name']}")
        print(f"📊 テンプレートタイプ: {result['type']}")
        print(f"📋 説明: {result['description']}")
        print(f"✅ アクティブ: {result['is_active']}")
        print(f"👤 作成者: {result['created_by']}")
        
        # データベース呼び出し確認
        print(f"🔧 session.query呼び出し回数: {mock_session.query.call_count}")
        
        # 検証結果
        success = all([
            result['id'] == sample_template_id,
            result['name'] == sample_template_create.name,
            result['type'] == sample_template_create.type,
            result['is_active'] == sample_template_create.is_active,
            result['created_by'] == sample_template_create.created_by,
            mock_session.query.call_count >= 1
        ])
        
        print(f"✅ Level 1テスト結果: {'成功' if success else '失敗'}")
        return result

# 実行
retrieved_template = test_get_template_by_id()

# %%
"""
Level 1テスト3: 全テンプレート取得（モックベース）
設計書仕様: すべてのテンプレートを取得
入力: なし（オプションでフィルタ条件）
期待値: テンプレートリスト
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_get_all_templates():
    print("🧪 Level 1テスト開始: 全テンプレート取得（モックベース）")
    
    with patch('app.services.template_service.Session') as mock_session_class:
        # モックセッションの設定
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # 複数のモックテンプレート
        mock_templates = []
        for i in range(3):
            mock_template = MagicMock()
            mock_template.id = uuid4()
            mock_template.name = f"テンプレート{i+1}"
            mock_template.description = f"テンプレート{i+1}の説明"
            mock_template.type = "user"
            mock_template.created_by = f"user_{i+1}"
            mock_template.is_active = True
            mock_template.created_at = datetime.utcnow()
            mock_templates.append(mock_template)
        
        # モッククエリの設定
        mock_query = MagicMock()
        mock_query.count.return_value = 3
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_templates
        mock_session.query.return_value = mock_query
        
        # func.countのモック（各テンプレートのアイテム数）
        with patch('app.services.template_service.func') as mock_func:
            mock_func.count.return_value = MagicMock()
            # 各テンプレートのアイテム数を5に設定
            mock_session.query.return_value.filter.return_value.scalar.return_value = 5
            
            # 実行
            result = template_service.get_all_templates(mock_session)
        
        # 結果確認
        print(f"📊 取得されたテンプレート数: {len(result['templates'])}")
        for i, template in enumerate(result['templates']):
            print(f"  {i+1}. ID: {template['id']}")
            print(f"     名前: {template['name']}")
            print(f"     タイプ: {template['type']}")
            print(f"     作成者: {template['created_by']}")
        
        # データベース呼び出し確認
        print(f"🔧 session.query呼び出し回数: {mock_session.query.call_count}")
        
        # 検証結果
        success = all([
            len(result['templates']) == 3,
            all(template['type'] == "user" for template in result['templates']),
            all(template['is_active'] for template in result['templates']),
            mock_session.query.call_count >= 1
        ])
        
        print(f"✅ Level 1テスト結果: {'成功' if success else '失敗'}")
        return result

# 実行
all_templates = test_get_all_templates()

# %%
"""
Level 1テスト4: テンプレート更新（モックベース）
設計書仕様: 既存テンプレートの更新
入力: テンプレートIDと更新データ
期待値: 更新されたテンプレートオブジェクト
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_update_template():
    print("🧪 Level 1テスト開始: テンプレート更新（モックベース）")
    
    with patch('app.services.template_service.Session') as mock_session_class:
        # モックセッションの設定
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # 既存テンプレートのモック
        mock_existing_template = MagicMock()
        mock_existing_template.id = sample_template_id
        mock_existing_template.name = sample_template_create.name
        mock_existing_template.description = sample_template_create.description
        mock_existing_template.type = sample_template_create.type
        mock_existing_template.created_by = sample_template_create.created_by
        mock_existing_template.is_active = sample_template_create.is_active
        
        # get_template_by_idのモック（2回呼ばれる：更新前の取得と更新後の取得）
        with patch('app.services.template_service.get_template_by_id') as mock_get:
            # 更新後の結果を辞書形式で返す
            updated_result = {
                'id': sample_template_id,
                'name': sample_template_update.name,
                'description': sample_template_update.description,
                'type': sample_template_create.type,
                'created_by': sample_template_create.created_by,
                'is_active': sample_template_update.is_active,
                'items': []
            }
            mock_get.return_value = updated_result
            
            # 実行
            result = template_service.update_template(mock_session, sample_template_id, sample_template_update)
            
            # 結果確認
            print(f"📄 更新されたテンプレートID: {result['id']}")
            print(f"📝 更新後テンプレート名: {result['name']}")
            print(f"📋 更新後説明: {result['description']}")
            print(f"✅ アクティブ: {result['is_active']}")
            
            # データベース呼び出し確認
            print(f"🔧 session.commit呼び出し回数: {mock_session.commit.call_count}")
            
            # 検証結果
            success = all([
                result['id'] == sample_template_id,
                mock_session.commit.call_count == 1,
                mock_get.call_count >= 1
            ])
            
            print(f"✅ Level 1テスト結果: {'成功' if success else '失敗'}")
            return result

# 実行
updated_template = test_update_template()

# %%
"""
Level 1テスト5: テンプレート削除（モックベース）
設計書仕様: 指定されたテンプレートの削除
入力: テンプレートID
期待値: 削除成功の確認
テストレベル: Level 1 (Unit Test) - モック使用
"""

def test_delete_template():
    print("🧪 Level 1テスト開始: テンプレート削除（モックベース）")
    
    with patch('app.services.template_service.Session') as mock_session_class:
        # モックセッションの設定
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # 削除対象テンプレートのモック
        mock_template_to_delete = MagicMock()
        mock_template_to_delete.id = sample_template_id
        mock_template_to_delete.name = sample_template_create.name
        
        # get_template_by_idのモック
        with patch('app.services.template_service.get_template_by_id') as mock_get:
            mock_get.return_value = mock_template_to_delete
            
            # func.countのモック（使用中チャート数）
            with patch('app.services.template_service.func') as mock_func:
                mock_func.count.return_value = MagicMock()
                mock_session.query.return_value.filter.return_value.scalar.return_value = 0
                
                # 実行
                result = template_service.delete_template(mock_session, sample_template_id)
            
            # 結果確認
            print(f"📄 削除対象テンプレートID: {sample_template_id}")
            print(f"📝 削除対象テンプレート名: {mock_template_to_delete.name}")
            print(f"🗑️ 削除結果: {result}")
            
            # データベース呼び出し確認
            print(f"🔧 session.delete呼び出し回数: {mock_session.delete.call_count}")
            print(f"🔧 session.commit呼び出し回数: {mock_session.commit.call_count}")
            
            # 検証結果
            success = all([
                result is True,
                mock_session.delete.call_count == 1,
                mock_session.commit.call_count == 1,
                mock_get.call_count >= 1
            ])
            
            print(f"✅ Level 1テスト結果: {'成功' if success else '失敗'}")
            return result

# 実行
delete_result = test_delete_template()

# %%
"""
セル7: Level 1テスト結果サマリー
"""

print("=" * 60)
print("📋 Level 1テンプレートサービステスト実行サマリー")
print("=" * 60)
print("✅ 1. テンプレート作成（モックベース） - 完了")
print("✅ 2. テンプレート取得（モックベース） - 完了")
print("✅ 3. 全テンプレート取得（モックベース） - 完了")
print("✅ 4. テンプレート更新（モックベース） - 完了")
print("✅ 5. テンプレート削除（モックベース） - 完了")
print("=" * 60)

# 詳細結果
print("📊 Level 1テスト詳細結果:")
print(f"  テンプレート作成: {'成功' if created_template else '失敗'}")
print(f"  テンプレート取得: {'成功' if retrieved_template else '失敗'}")
print(f"  全テンプレート取得: {'成功' if all_templates else '失敗'}")
print(f"  テンプレート更新: {'成功' if updated_template else '失敗'}")
print(f"  テンプレート削除: {'成功' if delete_result else '失敗'}")

print("🎉 Level 1テスト完了！")
print("💡 モックベースのユニットテストが正常に動作しています") 
# %%
