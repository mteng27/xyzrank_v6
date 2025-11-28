"""测试后端API"""
import asyncio
import httpx
from datetime import date


BASE_URL = "http://localhost:8000"


async def test_health():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
            return response.status_code == 200
        except httpx.ConnectError:
            print("❌ 无法连接到服务，请确保服务已启动")
            return False


async def test_list_podcasts():
    """测试获取播客列表"""
    print("\n=== 测试获取播客列表 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/podcasts/?skip=0&limit=10")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"返回播客数: {len(data)}")
            if data:
                print(f"第一个播客: {data[0].get('name', 'N/A')}")
            return True
        else:
            print(f"错误: {response.text}")
            return False


async def test_get_podcast_detail():
    """测试获取播客详情"""
    print("\n=== 测试获取播客详情 ===")
    async with httpx.AsyncClient() as client:
        # 先获取一个播客ID
        list_response = await client.get(f"{BASE_URL}/api/podcasts/?skip=0&limit=1")
        if list_response.status_code == 200:
            podcasts = list_response.json()
            if podcasts:
                podcast_id = podcasts[0]['id']
                response = await client.get(f"{BASE_URL}/api/podcasts/{podcast_id}")
                print(f"状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"播客名称: {data.get('name', 'N/A')}")
                    print(f"分类: {data.get('category', 'N/A')}")
                    return True
        print("❌ 无法获取播客详情")
        return False


async def test_get_metrics():
    """测试获取播客指标"""
    print("\n=== 测试获取播客指标 ===")
    async with httpx.AsyncClient() as client:
        # 先获取一个播客ID
        list_response = await client.get(f"{BASE_URL}/api/podcasts/?skip=0&limit=1")
        if list_response.status_code == 200:
            podcasts = list_response.json()
            if podcasts:
                podcast_id = podcasts[0]['id']
                response = await client.get(f"{BASE_URL}/api/podcasts/{podcast_id}/metrics")
                print(f"状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"指标记录数: {len(data)}")
                    if data:
                        latest = data[0]
                        print(f"最新记录: {latest.get('snapshot_date')} - {latest.get('subscriber_count'):,} 订阅者")
                    return True
        print("❌ 无法获取播客指标")
        return False


async def test_category_filter():
    """测试分类筛选"""
    print("\n=== 测试分类筛选 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/podcasts/?category=商业&limit=5")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"商业类播客数: {len(data)}")
            if data:
                print("示例:")
                for p in data[:3]:
                    print(f"  - {p.get('name', 'N/A')}")
            return True
        else:
            print(f"错误: {response.text}")
            return False


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("后端API测试")
    print("=" * 60)
    
    # 测试健康检查
    if not await test_health():
        print("\n❌ 服务未运行，请先启动服务:")
        print("   uvicorn app.main:app --reload")
        return
    
    # 运行其他测试
    results = []
    results.append(("获取播客列表", await test_list_podcasts()))
    results.append(("获取播客详情", await test_get_podcast_detail()))
    results.append(("获取播客指标", await test_get_metrics()))
    results.append(("分类筛选", await test_category_filter()))
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print(f"API文档: {BASE_URL}/docs")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())


