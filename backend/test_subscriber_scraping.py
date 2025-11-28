"""测试小宇宙平台订阅数抓取方法

分析不同的抓取方式：
1. 静态页面解析（BeautifulSoup）
2. 动态页面渲染（Playwright）
3. API调用（如果存在）
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from httpx import AsyncClient
from bs4 import BeautifulSoup
import re

# 尝试导入Playwright（如果已安装）
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright未安装，将只测试静态页面解析")

from sqlalchemy import select
from app.db.session import AsyncSessionFactory
from app.models.podcast import Podcast


class SubscriberScraperTester:
    """订阅数抓取测试器"""
    
    def __init__(self):
        self.client = AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self.results: List[Dict] = []
    
    async def test_static_parsing(self, xyz_id: str, url: str) -> Dict:
        """
        测试静态页面解析方法
        
        尝试从HTML中提取订阅数
        """
        result = {
            "method": "static_parsing",
            "xyz_id": xyz_id,
            "url": url,
            "success": False,
            "subscriber_count": None,
            "found_patterns": [],
            "html_snippets": [],
            "error": None,
            "status_code": None
        }
        
        try:
            response = await self.client.get(url, timeout=30.0)
            result["status_code"] = response.status_code
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            html_text = response.text
            
            # 方法1: 查找包含"订阅"的文本
            subscriber_texts = soup.find_all(string=re.compile(r'订阅|订阅者|订阅数|subscriber', re.I))
            if subscriber_texts:
                result["found_patterns"].append(f"找到包含'订阅'的文本 ({len(subscriber_texts)}个)")
                for text in subscriber_texts[:10]:  # 记录前10个
                    text_str = str(text).strip()
                    result["html_snippets"].append(text_str[:200])
                    # 尝试从文本中提取数字
                    numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', text_str)
                    if numbers:
                        result["found_patterns"].append(f"  文本中的数字: {numbers}")
            
            # 方法2: 查找数字模式（可能是订阅数）
            # 常见的订阅数格式：1234、1.2万、12.3万等
            # 特别注意：小宇宙的格式可能是 "1450035已订阅"（数字紧挨着，无空格）
            number_patterns = [
                r'(\d{4,})已订阅',  # 小宇宙格式：至少4位数字紧挨着"已订阅"（无空格）
                r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+已订阅',  # 有空格的情况
                r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[万萬]?\s*订阅',
                r'订阅[：:]\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[万萬]?',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*人订阅',
                r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*订阅者',
            ]
            
            for pattern in number_patterns:
                matches = re.findall(pattern, html_text, re.I)
                if matches:
                    result["found_patterns"].append(f"正则匹配: {pattern}")
                    # 尝试解析数字
                    for match in matches[:3]:  # 只记录前3个匹配
                        try:
                            # 处理"万"单位
                            if '万' in str(match) or '萬' in str(match):
                                num_str = re.sub(r'[万萬]', '', str(match))
                                num = float(num_str.replace(',', '')) * 10000
                            else:
                                num = int(str(match).replace(',', ''))
                            
                            # 如果数字合理（大于1000，小于1亿）- 提高下限避免误匹配
                            if 1000 < num < 100000000:
                                result["subscriber_count"] = int(num)
                                result["success"] = True
                                result["found_patterns"].append(f"提取到订阅数: {int(num)}")
                                break
                        except:
                            pass
            
            # 方法3: 查找data属性或JSON数据
            # 很多现代网站会在script标签中嵌入JSON数据
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.string or ""
                # 查找可能的JSON数据
                if 'subscriber' in script_text.lower() or '订阅' in script_text or 'subscribe' in script_text.lower():
                    result["found_patterns"].append("在script标签中找到订阅相关数据")
                    # 尝试提取JSON
                    json_matches = re.findall(r'\{[^{}]*"subscriber[^}]*\}', script_text, re.I)
                    if json_matches:
                        result["html_snippets"].append(f"JSON匹配: {json_matches[0][:300]}")
                    # 也尝试查找数字
                    numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', script_text)
                    if numbers and len(numbers) > 0:
                        # 查找较大的数字（可能是订阅数）
                        large_numbers = [n for n in numbers if len(n.replace(',', '')) >= 3]
                        if large_numbers:
                            result["found_patterns"].append(f"script中的大数字: {large_numbers[:5]}")
                            result["html_snippets"].append(f"script片段: {script_text[:500]}")
            
            # 方法4: 查找特定的class或id
            # 常见的订阅数显示元素
            possible_selectors = [
                {'class': re.compile(r'subscriber|订阅', re.I)},
                {'id': re.compile(r'subscriber|订阅', re.I)},
                {'data-subscriber': True},
            ]
            
            for selector in possible_selectors:
                elements = soup.find_all(attrs=selector)
                if elements:
                    result["found_patterns"].append(f"找到可能的订阅数元素: {selector}")
                    for elem in elements[:3]:
                        text = elem.get_text().strip()
                        # 尝试从文本中提取数字
                        numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', text)
                        if numbers:
                            result["html_snippets"].append(f"元素文本: {text[:100]}")
            
            # 方法5: 查找meta标签
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                content = meta.get('content', '')
                if '订阅' in content or 'subscriber' in content.lower():
                    result["found_patterns"].append("在meta标签中找到订阅相关信息")
                    result["html_snippets"].append(f"meta content: {content[:100]}")
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def test_dynamic_rendering(self, xyz_id: str, url: str) -> Dict:
        """
        测试动态页面渲染方法（使用Playwright）
        """
        result = {
            "method": "dynamic_rendering",
            "xyz_id": xyz_id,
            "url": url,
            "success": False,
            "subscriber_count": None,
            "page_title": None,
            "found_elements": [],
            "error": None
        }
        
        if not PLAYWRIGHT_AVAILABLE:
            result["error"] = "Playwright未安装"
            return result
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 设置视口大小
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # 访问页面
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # 获取页面标题
                result["page_title"] = await page.title()
                
                # 等待页面加载（给JavaScript一些时间，特别是动态内容）
                await page.wait_for_timeout(3000)  # 增加到3秒
                
                # 尝试等待包含"已订阅"的元素出现
                try:
                    await page.wait_for_selector('text=/已订阅/', timeout=5000)
                except:
                    pass  # 如果找不到也不影响后续处理
                
                # 方法1: 查找包含"已订阅"的文本元素（优先）
                # 小宇宙格式：数字+已订阅
                # 注意：订阅数在父元素中，需要获取父元素的文本
                subscriber_elements = await page.query_selector_all('text=/已订阅/i')
                if subscriber_elements:
                    result["found_elements"].append(f"找到 {len(subscriber_elements)} 个包含'已订阅'的元素")
                    for i, elem in enumerate(subscriber_elements[:5]):
                        # 获取文本节点的文本（可能只是"已订阅"）
                        text = await elem.text_content()
                        # 获取父元素的完整文本（包含数字）
                        parent = await elem.evaluate_handle('el => el.parentElement')
                        if parent:
                            parent_elem = parent.as_element()
                            if parent_elem:
                                parent_text = await parent_elem.text_content()
                                result["found_elements"].append(f"元素{i+1}: 文本={text}, 父元素文本={parent_text[:100]}")
                                
                                # 从父元素文本中提取数字（格式：数字已订阅）
                                # 优先匹配紧挨着的格式，要求至少6位数字（因为订阅数通常很大）
                                # 匹配所有可能的数字，然后选择最大的（最可能是订阅数）
                                tight_matches = re.findall(r'(\d{6,})已订阅', parent_text or "")
                                if tight_matches:
                                    # 转换为整数并选择最大的
                                    nums = [int(m) for m in tight_matches]
                                    num = max(nums)
                                    if 100000 <= num < 100000000:  # 至少10万，最多1亿
                                        result["subscriber_count"] = num
                                        result["success"] = True
                                        result["found_elements"].append(f"从多个匹配中选择最大数字: {num:,}")
                                        break
                                
                                # 如果没有6位以上的数字，尝试4-5位数字（但需要验证合理性）
                                tight_matches_short = re.findall(r'(\d{4,5})已订阅', parent_text or "")
                                if tight_matches_short:
                                    nums = [int(m) for m in tight_matches_short]
                                    num = max(nums)
                                    # 对于4-5位数字，需要更严格的验证
                                    if 10000 <= num < 1000000:  # 至少1万，最多100万
                                        result["subscriber_count"] = num
                                        result["success"] = True
                                        result["found_elements"].append(f"从短数字匹配中选择: {num:,}")
                                        break
                                
                                # 备用：匹配有空格的情况（带千位分隔符）
                                space_match = re.search(r'(\d{1,3}(?:,\d{3})+)\s+已订阅', parent_text or "")
                                if space_match:
                                    num = int(space_match.group(1).replace(',', ''))
                                    if 100000 <= num < 100000000:
                                        result["subscriber_count"] = num
                                        result["success"] = True
                                        break
                        else:
                            # 如果没有父元素，直接从文本中提取
                            tight_match = re.search(r'(\d{4,})已订阅', text or "")
                            if tight_match:
                                num = int(tight_match.group(1))
                                if 1000 <= num < 100000000:
                                    result["subscriber_count"] = num
                                    result["success"] = True
                                    break
                
                # 方法1b: 如果没找到，尝试查找包含"订阅"的其他元素
                if not result["success"]:
                    subscriber_elements = await page.query_selector_all('text=/订阅|订阅者|订阅数/i')
                    if subscriber_elements:
                        result["found_elements"].append(f"找到 {len(subscriber_elements)} 个包含'订阅'的元素")
                        for i, elem in enumerate(subscriber_elements[:5]):
                            text = await elem.text_content()
                            # 尝试从文本中提取数字
                            numbers = re.findall(r'\d{4,}', text or "")
                            if numbers:
                                for num_str in numbers:
                                    try:
                                        num = int(num_str)
                                        if 1000 <= num < 100000000:
                                            result["subscriber_count"] = num
                                            result["success"] = True
                                            break
                                    except:
                                        pass
                            if result["success"]:
                                break
                
                # 方法2: 查找可能的订阅数显示区域
                # 尝试常见的class或id选择器
                possible_selectors = [
                    '[class*="subscriber"]',
                    '[class*="订阅"]',
                    '[id*="subscriber"]',
                    '[id*="订阅"]',
                    '[data-subscriber]',
                ]
                
                for selector in possible_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            result["found_elements"].append(f"找到元素: {selector} ({len(elements)}个)")
                            for elem in elements[:3]:
                                text = await elem.text_content()
                                if text:
                                    result["found_elements"].append(f"文本: {text[:100]}")
                    except:
                        pass
                
                # 方法3: 获取页面HTML并解析
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                # 查找数字模式
                number_patterns = [
                    r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[万萬]?\s*订阅',
                    r'订阅[：:]\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[万萬]?',
                ]
                
                for pattern in number_patterns:
                    matches = re.findall(pattern, html, re.I)
                    if matches:
                        for match in matches:
                            try:
                                if '万' in str(match) or '萬' in str(match):
                                    num_str = re.sub(r'[万萬]', '', str(match))
                                    num = float(num_str.replace(',', '')) * 10000
                                else:
                                    num = int(str(match).replace(',', ''))
                                
                                if 100 < num < 100000000:
                                    result["subscriber_count"] = int(num)
                                    result["success"] = True
                                    break
                            except:
                                pass
                
                await browser.close()
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def test_api_call(self, xyz_id: str) -> Dict:
        """
        测试API调用方法
        
        尝试常见的API端点
        """
        result = {
            "method": "api_call",
            "xyz_id": xyz_id,
            "success": False,
            "subscriber_count": None,
            "tested_endpoints": [],
            "error": None
        }
        
        # 可能的API端点
        possible_endpoints = [
            f"https://api.xiaoyuzhoufm.com/podcast/{xyz_id}",
            f"https://api.xiaoyuzhoufm.com/v1/podcast/{xyz_id}",
            f"https://www.xiaoyuzhoufm.com/api/podcast/{xyz_id}",
            f"https://www.xiaoyuzhoufm.com/api/v1/podcast/{xyz_id}",
            f"https://www.xiaoyuzhoufm.com/podcast/{xyz_id}/api",
            f"https://www.xiaoyuzhoufm.com/podcast/{xyz_id}/stats",
        ]
        
        for endpoint in possible_endpoints:
            result["tested_endpoints"].append(endpoint)
            try:
                response = await self.client.get(endpoint)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # 尝试查找订阅数字段
                        possible_keys = ['subscriber_count', 'subscribers', 'subscribe_count', '订阅数', '订阅者数']
                        for key in possible_keys:
                            if key in data:
                                result["subscriber_count"] = data[key]
                                result["success"] = True
                                result["found_endpoint"] = endpoint
                                break
                    except:
                        pass
            except:
                pass
        
        return result
    
    async def test_single_podcast(self, xyz_id: str, name: str) -> Dict:
        """
        测试单个播客的所有方法
        """
        url = f"https://www.xiaoyuzhoufm.com/podcast/{xyz_id}"
        
        print(f"\n{'='*60}")
        print(f"测试播客: {name} ({xyz_id})")
        print(f"URL: {url}")
        print(f"{'='*60}")
        
        results = {
            "xyz_id": xyz_id,
            "name": name,
            "url": url,
            "methods": {}
        }
        
        # 测试静态页面解析
        print("\n[1/3] 测试静态页面解析...")
        static_result = await self.test_static_parsing(xyz_id, url)
        results["methods"]["static_parsing"] = static_result
        if static_result["success"]:
            print(f"  ✅ 成功! 订阅数: {static_result['subscriber_count']:,}")
        else:
            print(f"  ❌ 失败: {static_result.get('error', '未找到订阅数')}")
            if static_result.get("found_patterns"):
                print(f"  找到的模式: {len(static_result['found_patterns'])} 个")
        
        # 测试动态页面渲染
        if PLAYWRIGHT_AVAILABLE:
            print("\n[2/3] 测试动态页面渲染...")
            dynamic_result = await self.test_dynamic_rendering(xyz_id, url)
            results["methods"]["dynamic_rendering"] = dynamic_result
            if dynamic_result["success"]:
                print(f"  ✅ 成功! 订阅数: {dynamic_result['subscriber_count']:,}")
            else:
                print(f"  ❌ 失败: {dynamic_result.get('error', '未找到订阅数')}")
        else:
            print("\n[2/3] 跳过动态页面渲染（Playwright未安装）")
        
        # 测试API调用
        print("\n[3/3] 测试API调用...")
        api_result = await self.test_api_call(xyz_id)
        results["methods"]["api_call"] = api_result
        if api_result["success"]:
            print(f"  ✅ 成功! 订阅数: {api_result['subscriber_count']:,}")
            print(f"  找到的API端点: {api_result.get('found_endpoint')}")
        else:
            print(f"  ❌ 失败: 未找到可用的API端点")
        
        # 总结
        successful_methods = [k for k, v in results["methods"].items() if v.get("success")]
        if successful_methods:
            print(f"\n✅ 成功的方法: {', '.join(successful_methods)}")
            # 选择第一个成功的方法的结果
            for method in successful_methods:
                results["final_subscriber_count"] = results["methods"][method]["subscriber_count"]
                results["final_method"] = method
                break
        else:
            print(f"\n❌ 所有方法都失败了")
            results["final_subscriber_count"] = None
            results["final_method"] = None
        
        return results
    
    async def test_batch(self, podcasts: List[tuple], limit: int = 10) -> List[Dict]:
        """
        批量测试播客
        """
        test_podcasts = podcasts[:limit]
        print(f"\n{'='*60}")
        print(f"开始批量测试 {len(test_podcasts)} 个播客")
        print(f"{'='*60}")
        
        results = []
        for i, (xyz_id, name) in enumerate(test_podcasts, 1):
            print(f"\n[{i}/{len(test_podcasts)}]")
            result = await self.test_single_podcast(xyz_id, name)
            results.append(result)
            # 避免请求过快
            await asyncio.sleep(1)
        
        return results
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """
        生成测试报告
        """
        total = len(results)
        successful = sum(1 for r in results if r.get("final_subscriber_count") is not None)
        
        method_stats = {
            "static_parsing": {"success": 0, "total": 0},
            "dynamic_rendering": {"success": 0, "total": 0},
            "api_call": {"success": 0, "total": 0},
        }
        
        for result in results:
            for method_name, method_result in result.get("methods", {}).items():
                if method_name in method_stats:
                    method_stats[method_name]["total"] += 1
                    if method_result.get("success"):
                        method_stats[method_name]["success"] += 1
        
        report = {
            "test_time": datetime.now().isoformat(),
            "total_tested": total,
            "successful": successful,
            "success_rate": f"{successful/total*100:.2f}%" if total > 0 else "0%",
            "method_statistics": {
                method: {
                    "success": stats["success"],
                    "total": stats["total"],
                    "success_rate": f"{stats['success']/stats['total']*100:.2f}%" if stats["total"] > 0 else "0%"
                }
                for method, stats in method_stats.items()
            },
            "recommended_method": None,
            "sample_results": results[:5]  # 前5个结果作为示例
        }
        
        # 推荐最佳方法
        best_method = max(
            method_stats.items(),
            key=lambda x: x[1]["success"] / x[1]["total"] if x[1]["total"] > 0 else 0
        )
        if best_method[1]["total"] > 0 and best_method[1]["success"] > 0:
            report["recommended_method"] = best_method[0]
        
        return report
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


async def get_test_podcasts(limit: int = 10) -> List[tuple]:
    """从数据库获取测试播客"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Podcast).limit(limit)
        )
        podcasts = result.scalars().all()
        return [(p.xyz_id, p.name) for p in podcasts]


async def main():
    """主函数"""
    print("="*60)
    print("小宇宙平台订阅数抓取方法测试")
    print("="*60)
    
    # 获取测试播客
    print("\n📖 从数据库加载测试播客...")
    podcasts = await get_test_podcasts(limit=10)
    print(f"✅ 加载了 {len(podcasts)} 个播客")
    
    # 创建测试器
    tester = SubscriberScraperTester()
    
    try:
        # 执行批量测试
        results = await tester.test_batch(podcasts, limit=10)
        
        # 生成报告
        print("\n" + "="*60)
        print("测试报告")
        print("="*60)
        report = tester.generate_report(results)
        
        print(f"\n总测试数: {report['total_tested']}")
        print(f"成功数: {report['successful']} ({report['success_rate']})")
        print(f"\n方法统计:")
        for method, stats in report['method_statistics'].items():
            print(f"  {method}:")
            print(f"    成功: {stats['success']}/{stats['total']} ({stats['success_rate']})")
        
        if report['recommended_method']:
            print(f"\n✅ 推荐方法: {report['recommended_method']}")
        
        # 保存详细结果
        output_file = "subscriber_scraping_test_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "report": report,
                "detailed_results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细结果已保存到: {output_file}")
        
        # 显示成功示例
        successful = [r for r in results if r.get("final_subscriber_count")]
        if successful:
            print(f"\n✅ 成功示例:")
            for r in successful[:3]:
                print(f"  - {r['name']}: {r['final_subscriber_count']:,} 订阅者 (方法: {r['final_method']})")
    
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())

