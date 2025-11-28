"""批量测试播客数据抓取 - 检测100个网址的数据可用性"""
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from httpx import AsyncClient
from bs4 import BeautifulSoup
import json
import sys

# 简单的日志函数（如果loguru未安装）
try:
    from loguru import logger
    # 配置日志
    logger.add("scraper_test.log", rotation="10 MB", level="INFO")
except ImportError:
    class SimpleLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    logger = SimpleLogger()


class BatchScraperTester:
    """批量抓取测试器"""
    
    def __init__(self):
        self.client = AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        self.results: List[Dict] = []
    
    async def test_single_podcast(self, podcast_data: Dict) -> Dict:
        """
        测试单个播客的数据可用性
        
        Args:
            podcast_data: 包含 xyz_id 和 url 的字典
        
        Returns:
            测试结果字典
        """
        xyz_id = podcast_data['xyz_id']
        url = podcast_data['url']
        
        result = {
            "xyz_id": xyz_id,
            "url": url,
            "name": podcast_data.get('name'),
            "accessible": False,
            "has_title": False,
            "has_rss": False,
            "has_cover": False,
            "has_description": False,
            "status_code": None,
            "error": None,
            "data": {}
        }
        
        try:
            # 测试URL可访问性
            response = await self.client.get(url)
            result["status_code"] = response.status_code
            result["accessible"] = response.status_code == 200
            
            if not result["accessible"]:
                result["error"] = f"HTTP {response.status_code}"
                return result
            
            # 解析页面内容
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 检查标题
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()
                result["has_title"] = True
                result["data"]["title"] = title
            
            # 检查RSS链接
            rss_link = soup.find("link", {"type": "application/rss+xml"})
            if not rss_link:
                # 尝试其他方式查找RSS
                rss_link = soup.find("a", href=lambda x: x and "rss" in x.lower())
            
            if rss_link:
                result["has_rss"] = True
                href = rss_link.get("href") or (rss_link.text if hasattr(rss_link, 'text') else None)
                result["data"]["rss_url"] = href
            
            # 检查封面图
            og_image = soup.find("meta", {"property": "og:image"})
            if og_image:
                result["has_cover"] = True
                result["data"]["cover_url"] = og_image.get("content")
            else:
                # 尝试查找其他图片标签
                img_tag = soup.find("img", class_=lambda x: x and "cover" in str(x).lower())
                if img_tag:
                    result["has_cover"] = True
                    result["data"]["cover_url"] = img_tag.get("src")
            
            # 检查描述
            description_tag = soup.find("meta", {"name": "description"})
            if description_tag:
                result["has_description"] = True
                result["data"]["description"] = description_tag.get("content")
            else:
                # 尝试查找其他描述元素
                desc_tag = soup.find("p", class_=lambda x: x and "description" in str(x).lower())
                if desc_tag:
                    result["has_description"] = True
                    result["data"]["description"] = desc_tag.get_text()[:200]  # 限制长度
            
            # 尝试查找订阅者数量（如果页面中有）
            # 这需要根据实际页面结构调整
            subscriber_elements = soup.find_all(string=lambda text: text and "订阅" in text)
            if subscriber_elements:
                result["data"]["has_subscriber_info"] = True
            
            logger.info(f"✅ {xyz_id}: 可访问, 标题={result['has_title']}, RSS={result['has_rss']}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ {xyz_id}: {e}")
        
        return result
    
    async def test_batch(self, podcasts: List[Dict], limit: int = 100) -> List[Dict]:
        """
        批量测试播客
        
        Args:
            podcasts: 播客数据列表（包含 xyz_id 和 url）
            limit: 测试数量限制
        
        Returns:
            测试结果列表
        """
        test_podcasts = podcasts[:limit]
        logger.info(f"开始测试 {len(test_podcasts)} 个播客...")
        
        # 使用信号量控制并发数（避免请求过快）
        semaphore = asyncio.Semaphore(5)  # 最多5个并发请求
        
        async def test_with_semaphore(podcast_data: Dict):
            async with semaphore:
                return await self.test_single_podcast(podcast_data)
        
        # 批量测试
        tasks = [test_with_semaphore(podcast) for podcast in test_podcasts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        self.results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                podcast = test_podcasts[i]
                self.results.append({
                    "xyz_id": podcast.get('xyz_id', 'N/A'),
                    "url": podcast.get('url', 'N/A'),
                    "accessible": False,
                    "error": str(result)
                })
            else:
                self.results.append(result)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        total = len(self.results)
        accessible = sum(1 for r in self.results if r.get("accessible", False))
        has_title = sum(1 for r in self.results if r.get("has_title", False))
        has_rss = sum(1 for r in self.results if r.get("has_rss", False))
        has_cover = sum(1 for r in self.results if r.get("has_cover", False))
        has_description = sum(1 for r in self.results if r.get("has_description", False))
        errors = [r for r in self.results if r.get("error")]
        
        report = {
            "total": total,
            "accessible": accessible,
            "accessible_rate": f"{accessible/total*100:.2f}%" if total > 0 else "0%",
            "data_availability": {
                "has_title": has_title,
                "has_title_rate": f"{has_title/total*100:.2f}%" if total > 0 else "0%",
                "has_rss": has_rss,
                "has_rss_rate": f"{has_rss/total*100:.2f}%" if total > 0 else "0%",
                "has_cover": has_cover,
                "has_cover_rate": f"{has_cover/total*100:.2f}%" if total > 0 else "0%",
                "has_description": has_description,
                "has_description_rate": f"{has_description/total*100:.2f}%" if total > 0 else "0%",
            },
            "errors_count": len(errors),
            "error_samples": errors[:10]  # 前10个错误示例
        }
        
        return report
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


def load_podcast_data_from_excel(file_path: str, limit: int = 100) -> List[Dict]:
    """
    从Excel文件加载播客数据（包括ID和URL）
    
    Args:
        file_path: Excel文件路径
        limit: 加载数量限制
    
    Returns:
        播客数据列表，每个包含 xyz_id 和 url
    """
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Excel文件列名: {df.columns.tolist()}")
        
        # 提取数据
        podcasts = []
        for idx, row in df.head(limit).iterrows():
            # 尝试从link_url提取ID，或使用album_id
            link_url = str(row.get('link_url', '')).strip()
            album_id = str(row.get('album_id', '')).strip()
            
            # 从URL中提取ID
            xyz_id = album_id
            if link_url and link_url != 'nan':
                # 尝试从URL中提取ID
                if '/podcast/' in link_url:
                    xyz_id = link_url.split('/podcast/')[-1].split('?')[0].split('#')[0]
                url = link_url
            else:
                # 如果没有URL，使用ID构建URL
                url = f"https://www.xiaoyuzhoufm.com/podcast/{xyz_id}"
            
            if xyz_id and xyz_id != 'nan':
                podcasts.append({
                    'xyz_id': xyz_id,
                    'url': url,
                    'name': str(row.get('album_name', '')).strip() if pd.notna(row.get('album_name')) else None
                })
        
        logger.info(f"从Excel加载了 {len(podcasts)} 个播客数据，将测试前 {min(limit, len(podcasts))} 个")
        return podcasts[:limit]
        
    except Exception as e:
        logger.error(f"读取Excel文件失败: {e}")
        raise


async def main():
    """主函数"""
    print("=" * 60)
    print("批量测试播客数据抓取 - 检测数据可用性")
    print("=" * 60)
    print()
    
    # Excel文件路径
    excel_path = Path(__file__).parent.parent / "小宇宙专辑资料-all.xlsx"
    
    if not excel_path.exists():
        print(f"❌ Excel文件不存在: {excel_path}")
        print("请确保文件路径正确")
        return
    
    # 加载播客数据
    print("📖 读取Excel文件...")
    try:
        podcasts = load_podcast_data_from_excel(str(excel_path), limit=100)
        print(f"✅ 成功加载 {len(podcasts)} 个播客数据")
        print()
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return
    
    # 创建测试器
    tester = BatchScraperTester()
    
    try:
        # 执行批量测试
        print("🚀 开始批量测试...")
        print(f"测试数量: {len(podcasts)}")
        print("并发数: 5")
        print()
        
        start_time = datetime.now()
        results = await tester.test_batch(podcasts, limit=100)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        print(f"✅ 测试完成，耗时: {duration:.2f} 秒")
        print()
        
        # 生成报告
        print("=" * 60)
        print("测试报告")
        print("=" * 60)
        report = tester.generate_report()
        
        print(f"总测试数: {report['total']}")
        print(f"可访问: {report['accessible']} ({report['accessible_rate']})")
        print()
        print("数据可用性:")
        print(f"  - 有标题: {report['data_availability']['has_title']} ({report['data_availability']['has_title_rate']})")
        print(f"  - 有RSS: {report['data_availability']['has_rss']} ({report['data_availability']['has_rss_rate']})")
        print(f"  - 有封面: {report['data_availability']['has_cover']} ({report['data_availability']['has_cover_rate']})")
        print(f"  - 有描述: {report['data_availability']['has_description']} ({report['data_availability']['has_description_rate']})")
        print()
        print(f"错误数: {report['errors_count']}")
        
        if report['error_samples']:
            print("\n错误示例（前10个）:")
            for error in report['error_samples']:
                print(f"  - {error.get('xyz_id', 'N/A')}: {error.get('error', 'Unknown error')}")
        
        # 保存详细结果到JSON
        output_file = "scraper_test_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_time": datetime.now().isoformat(),
                "total_tested": len(results),
                "report": report,
                "detailed_results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细结果已保存到: {output_file}")
        print(f"📄 日志已保存到: scraper_test.log")
        
        # 显示一些成功示例
        successful = [r for r in results if r.get("accessible") and r.get("has_title")]
        if successful:
            print(f"\n✅ 成功示例（前5个）:")
            for r in successful[:5]:
                print(f"  - {r['xyz_id']}: {r['data'].get('title', 'N/A')}")
        
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())

