"""
Level 2 統合テスト: レポート生成
テストレベル: Level 2 (Integration)
信頼性: レポート生成 95%
実行頻度: 週次
前提条件: Level 2統合テスト実行後
設計書参照: doc_04_detailed_design.md
更新日: 2025-01-15

使用方法:
pytest tests/test_level2_report_generator.py -v -m integration
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import pytest


@dataclass
class Level2TestResult:
    """Level 2統合テスト結果"""
    test_name: str
    test_class: str
    test_method: str
    status: str  # "passed", "failed", "skipped"
    duration: float
    error_message: Optional[str] = None
    warnings: List[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.performance_metrics is None:
            self.performance_metrics = {}


@dataclass
class Level2TestSummary:
    """Level 2統合テストサマリー"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration: float
    success_rate: float
    test_categories: Dict[str, int]
    performance_summary: Dict[str, Any]
    generated_at: datetime
    
    def __post_init__(self):
        if self.test_categories is None:
            self.test_categories = {}
        if self.performance_summary is None:
            self.performance_summary = {}


class Level2TestReportGenerator:
    """Level 2統合テストレポート生成器"""
    
    def __init__(self, output_dir: str = "test_reports/level2"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_results: List[Level2TestResult] = []
        self.start_time = datetime.utcnow()
    
    def add_test_result(self, result: Level2TestResult):
        """テスト結果を追加"""
        self.test_results.append(result)
    
    def generate_summary(self) -> Level2TestSummary:
        """テストサマリーを生成"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == "passed"])
        failed_tests = len([r for r in self.test_results if r.status == "failed"])
        skipped_tests = len([r for r in self.test_results if r.status == "skipped"])
        
        total_duration = sum(r.duration for r in self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # テストカテゴリ分析
        test_categories = {}
        for result in self.test_results:
            category = self._extract_category(result.test_class)
            test_categories[category] = test_categories.get(category, 0) + 1
        
        # パフォーマンスサマリー
        performance_summary = self._generate_performance_summary()
        
        return Level2TestSummary(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            total_duration=total_duration,
            success_rate=success_rate,
            test_categories=test_categories,
            performance_summary=performance_summary,
            generated_at=datetime.utcnow()
        )
    
    def _extract_category(self, test_class: str) -> str:
        """テストクラス名からカテゴリを抽出"""
        if "API" in test_class:
            return "API統合"
        elif "Service" in test_class:
            return "サービス統合"
        elif "Database" in test_class:
            return "データベース統合"
        elif "Performance" in test_class:
            return "パフォーマンス"
        else:
            return "その他"
    
    def _generate_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリーを生成"""
        performance_results = [
            r for r in self.test_results 
            if r.performance_metrics and len(r.performance_metrics) > 0
        ]
        
        if not performance_results:
            return {}
        
        summary = {
            "total_performance_tests": len(performance_results),
            "average_response_time": 0,
            "max_response_time": 0,
            "min_response_time": float('inf'),
            "performance_warnings": []
        }
        
        response_times = []
        for result in performance_results:
            metrics = result.performance_metrics
            if "response_time" in metrics:
                response_times.append(metrics["response_time"])
            
            # パフォーマンス警告収集
            if result.warnings:
                for warning in result.warnings:
                    if "パフォーマンス" in warning:
                        summary["performance_warnings"].append({
                            "test": result.test_name,
                            "warning": warning
                        })
        
        if response_times:
            summary["average_response_time"] = sum(response_times) / len(response_times)
            summary["max_response_time"] = max(response_times)
            summary["min_response_time"] = min(response_times)
        
        return summary
    
    def generate_markdown_report(self, summary: Level2TestSummary) -> str:
        """Markdownレポートを生成"""
        report = f"""# Level 2 統合テスト レポート

## 📊 テスト実行サマリー

- **実行日時**: {summary.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **総テスト数**: {summary.total_tests}
- **成功**: {summary.passed_tests} ✅
- **失敗**: {summary.failed_tests} ❌
- **スキップ**: {summary.skipped_tests} ⏭️
- **成功率**: {summary.success_rate:.1f}%
- **総実行時間**: {summary.total_duration:.2f}秒

## 📈 テストカテゴリ別結果

| カテゴリ | テスト数 |
|---------|---------|
"""
        
        for category, count in summary.test_categories.items():
            report += f"| {category} | {count} |\n"
        
        report += f"""
## 🚀 パフォーマンス分析

"""
        
        if summary.performance_summary:
            perf = summary.performance_summary
            report += f"""- **パフォーマンステスト数**: {perf.get('total_performance_tests', 0)}
- **平均レスポンス時間**: {perf.get('average_response_time', 0):.3f}秒
- **最大レスポンス時間**: {perf.get('max_response_time', 0):.3f}秒
- **最小レスポンス時間**: {perf.get('min_response_time', 0):.3f}秒

"""
            
            if perf.get('performance_warnings'):
                report += "### ⚠️ パフォーマンス警告\n\n"
                for warning in perf['performance_warnings']:
                    report += f"- **{warning['test']}**: {warning['warning']}\n"
                report += "\n"
        else:
            report += "- パフォーマンステストは実行されませんでした\n\n"
        
        # 詳細テスト結果
        report += "## 📋 詳細テスト結果\n\n"
        
        # 成功したテスト
        passed_tests = [r for r in self.test_results if r.status == "passed"]
        if passed_tests:
            report += "### ✅ 成功したテスト\n\n"
            for result in passed_tests:
                report += f"- **{result.test_name}** ({result.duration:.2f}秒)\n"
                if result.warnings:
                    for warning in result.warnings:
                        report += f"  - ⚠️ {warning}\n"
            report += "\n"
        
        # 失敗したテスト
        failed_tests = [r for r in self.test_results if r.status == "failed"]
        if failed_tests:
            report += "### ❌ 失敗したテスト\n\n"
            for result in failed_tests:
                report += f"- **{result.test_name}** ({result.duration:.2f}秒)\n"
                if result.error_message:
                    report += f"  - エラー: `{result.error_message}`\n"
            report += "\n"
        
        # スキップされたテスト
        skipped_tests = [r for r in self.test_results if r.status == "skipped"]
        if skipped_tests:
            report += "### ⏭️ スキップされたテスト\n\n"
            for result in skipped_tests:
                report += f"- **{result.test_name}**\n"
                if result.error_message:
                    report += f"  - 理由: {result.error_message}\n"
            report += "\n"
        
        # 推奨事項
        report += self._generate_recommendations(summary)
        
        return report
    
    def _generate_recommendations(self, summary: Level2TestSummary) -> str:
        """推奨事項を生成"""
        recommendations = "## 💡 推奨事項\n\n"
        
        # 成功率に基づく推奨事項
        if summary.success_rate < 80:
            recommendations += "- ⚠️ **成功率が80%を下回っています**。失敗したテストの原因を調査し、修正してください。\n"
        elif summary.success_rate < 95:
            recommendations += "- 📈 成功率は良好ですが、さらなる改善の余地があります。\n"
        else:
            recommendations += "- ✅ 優秀な成功率です。現在の品質を維持してください。\n"
        
        # パフォーマンスに基づく推奨事項
        if summary.performance_summary:
            perf = summary.performance_summary
            avg_time = perf.get('average_response_time', 0)
            
            if avg_time > 2.0:
                recommendations += "- 🐌 **平均レスポンス時間が2秒を超えています**。パフォーマンスの最適化を検討してください。\n"
            elif avg_time > 1.0:
                recommendations += "- ⏱️ レスポンス時間に改善の余地があります。\n"
            
            if perf.get('performance_warnings'):
                recommendations += "- ⚠️ パフォーマンス警告が発生しています。詳細を確認してください。\n"
        
        # テストカバレッジに基づく推奨事項
        if summary.total_tests < 10:
            recommendations += "- 📊 **テスト数が少ない可能性があります**。追加のテストケースを検討してください。\n"
        
        # 失敗テストに基づく推奨事項
        if summary.failed_tests > 0:
            recommendations += f"- 🔧 {summary.failed_tests}件の失敗テストがあります。優先的に修正してください。\n"
        
        recommendations += "\n"
        return recommendations
    
    def save_json_report(self, summary: Level2TestSummary, filename: str = None) -> str:
        """JSONレポートを保存"""
        if filename is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"level2_integration_test_report_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        report_data = {
            "summary": asdict(summary),
            "test_results": [asdict(result) for result in self.test_results],
            "metadata": {
                "report_version": "1.0",
                "generator": "Level2TestReportGenerator",
                "test_level": "Level 2 (Integration)"
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        return str(filepath)
    
    def save_markdown_report(self, summary: Level2TestSummary, filename: str = None) -> str:
        """Markdownレポートを保存"""
        if filename is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"level2_integration_test_report_{timestamp}.md"
        
        filepath = self.output_dir / filename
        
        markdown_content = self.generate_markdown_report(summary)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(filepath)


class TestLevel2ReportGeneration:
    """
    Level 2 統合テスト: レポート生成テスト
    """
    
    @pytest.mark.integration
    def test_level2_report_generator_functionality(self):
        """
        テストレベル: Level 2 (Integration)
        対象: レポート生成機能統合テスト
        """
        print("\n🧪 Level 2統合テスト開始: レポート生成機能")
        
        # Step 1: レポート生成器初期化
        print("📋 Step 1: レポート生成器初期化")
        generator = Level2TestReportGenerator("test_reports/level2_test")
        
        # Step 2: サンプルテスト結果追加
        print("📊 Step 2: サンプルテスト結果追加")
        
        # 成功テスト結果
        generator.add_test_result(Level2TestResult(
            test_name="チャートアップロードAPI統合",
            test_class="TestLevel2ChartAPIIntegration",
            test_method="test_chart_upload_api_integration",
            status="passed",
            duration=2.5,
            performance_metrics={"response_time": 1.2, "throughput": 10}
        ))
        
        generator.add_test_result(Level2TestResult(
            test_name="テンプレートCRUD統合",
            test_class="TestLevel2TemplateServiceIntegration",
            test_method="test_template_crud_integration",
            status="passed",
            duration=1.8,
            warnings=["DB接続が一時的に遅延しました"]
        ))
        
        # 失敗テスト結果
        generator.add_test_result(Level2TestResult(
            test_name="GCS統合テスト",
            test_class="TestLevel2GCSDBServiceIntegration",
            test_method="test_gcs_integration",
            status="failed",
            duration=0.5,
            error_message="GCS認証エラー"
        ))
        
        # スキップテスト結果
        generator.add_test_result(Level2TestResult(
            test_name="外部API統合テスト",
            test_class="TestLevel2ExternalAPIIntegration",
            test_method="test_external_api_integration",
            status="skipped",
            duration=0.0,
            error_message="テスト環境制限"
        ))
        
        # パフォーマンステスト結果
        generator.add_test_result(Level2TestResult(
            test_name="一括操作パフォーマンス",
            test_class="TestLevel2DatabasePerformanceIntegration",
            test_method="test_bulk_operations_integration",
            status="passed",
            duration=5.2,
            warnings=["作成パフォーマンス警告: 0.6秒 > 0.5秒"],
            performance_metrics={
                "response_time": 3.1,
                "creation_per_item": 0.6,
                "update_per_item": 0.2,
                "retrieval_per_item": 0.1
            }
        ))
        
        print(f"✅ テスト結果追加完了: {len(generator.test_results)}件")
        
        # Step 3: サマリー生成
        print("📈 Step 3: サマリー生成")
        summary = generator.generate_summary()
        
        assert summary.total_tests == 5
        assert summary.passed_tests == 3
        assert summary.failed_tests == 1
        assert summary.skipped_tests == 1
        assert summary.success_rate == 60.0  # 3/5 * 100
        
        print(f"✅ サマリー生成完了: 成功率 {summary.success_rate}%")
        
        # Step 4: JSONレポート生成
        print("💾 Step 4: JSONレポート生成")
        json_filepath = generator.save_json_report(summary, "test_level2_report.json")
        
        assert os.path.exists(json_filepath)
        
        # JSONファイル内容確認
        with open(json_filepath, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        assert "summary" in json_data
        assert "test_results" in json_data
        assert "metadata" in json_data
        assert json_data["summary"]["total_tests"] == 5
        
        print(f"✅ JSONレポート生成完了: {json_filepath}")
        
        # Step 5: Markdownレポート生成
        print("📝 Step 5: Markdownレポート生成")
        md_filepath = generator.save_markdown_report(summary, "test_level2_report.md")
        
        assert os.path.exists(md_filepath)
        
        # Markdownファイル内容確認
        with open(md_filepath, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        assert "# Level 2 統合テスト レポート" in md_content
        assert "📊 テスト実行サマリー" in md_content
        assert "🚀 パフォーマンス分析" in md_content
        assert "💡 推奨事項" in md_content
        assert "成功率: 60.0%" in md_content
        
        print(f"✅ Markdownレポート生成完了: {md_filepath}")
        
        # Step 6: レポート内容検証
        print("🔍 Step 6: レポート内容検証")
        
        # パフォーマンスサマリー確認
        assert summary.performance_summary["total_performance_tests"] == 2
        assert summary.performance_summary["average_response_time"] > 0
        assert len(summary.performance_summary["performance_warnings"]) == 1
        
        # テストカテゴリ確認
        assert "API統合" in summary.test_categories
        assert "サービス統合" in summary.test_categories
        assert "データベース統合" in summary.test_categories
        
        print("✅ レポート内容検証完了")
        
        print("✅ Level 2統合テスト完了: レポート生成機能")
    
    @pytest.mark.integration
    def test_level2_report_performance_analysis(self):
        """
        テストレベル: Level 2 (Integration)
        対象: パフォーマンス分析機能
        """
        print("\n🧪 Level 2統合テスト開始: パフォーマンス分析機能")
        
        # Step 1: パフォーマンステスト結果準備
        print("📊 Step 1: パフォーマンステスト結果準備")
        generator = Level2TestReportGenerator("test_reports/level2_performance")
        
        # 複数のパフォーマンステスト結果を追加
        performance_tests = [
            {"name": "API応答時間テスト", "response_time": 0.8, "status": "passed"},
            {"name": "DB操作パフォーマンス", "response_time": 1.5, "status": "passed"},
            {"name": "一括処理パフォーマンス", "response_time": 3.2, "status": "passed", "warning": "処理時間警告"},
            {"name": "同時接続パフォーマンス", "response_time": 2.1, "status": "failed", "error": "タイムアウト"},
        ]
        
        for i, test in enumerate(performance_tests):
            result = Level2TestResult(
                test_name=test["name"],
                test_class="TestLevel2PerformanceIntegration",
                test_method=f"test_performance_{i}",
                status=test["status"],
                duration=test["response_time"],
                performance_metrics={"response_time": test["response_time"]},
                error_message=test.get("error"),
                warnings=[test["warning"]] if test.get("warning") else []
            )
            generator.add_test_result(result)
        
        # Step 2: パフォーマンス分析
        print("📈 Step 2: パフォーマンス分析")
        summary = generator.generate_summary()
        
        perf_summary = summary.performance_summary
        assert perf_summary["total_performance_tests"] == 4
        assert perf_summary["average_response_time"] == (0.8 + 1.5 + 3.2 + 2.1) / 4
        assert perf_summary["max_response_time"] == 3.2
        assert perf_summary["min_response_time"] == 0.8
        assert len(perf_summary["performance_warnings"]) == 1
        
        print(f"✅ パフォーマンス分析完了: 平均 {perf_summary['average_response_time']:.2f}秒")
        
        # Step 3: パフォーマンスレポート生成
        print("📝 Step 3: パフォーマンスレポート生成")
        md_content = generator.generate_markdown_report(summary)
        
        assert "🚀 パフォーマンス分析" in md_content
        assert f"平均レスポンス時間: {perf_summary['average_response_time']:.3f}秒" in md_content
        assert "⚠️ パフォーマンス警告" in md_content
        
        print("✅ パフォーマンスレポート生成完了")
        
        print("✅ Level 2統合テスト完了: パフォーマンス分析機能")


if __name__ == "__main__":
    # 単体実行用
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "integration"]) 