"""简单的 API 测试脚本"""
import asyncio
import httpx
from datetime import date


BASE_URL = "http://localhost:8000"


async def test_health_check():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200


async def test_root():
    """测试根路径"""
    print("\n=== 测试根路径 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200


async def test_create_podcast():
    """测试创建播客"""
    print("\n=== 测试创建播客 ===")
    async with httpx.AsyncClient() as client:
        data = {
            "xyz_id": "test_xyz_001",
            "name": "测试播客",
            "category": "科技",
            "description": "这是一个测试播客"
        }
        response = await client.post(f"{BASE_URL}/api/podcasts/", json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        if response.status_code == 201:
            return response.json()["id"]
        return None


async def test_list_podcasts():
    """测试获取播客列表"""
    print("\n=== 测试获取播客列表 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/podcasts/?skip=0&limit=10")
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"播客数量: {len(data)}")
        if data:
            print(f"第一个播客: {data[0]}")
        return response.status_code == 200


async def test_get_podcast(podcast_id: int):
    """测试获取单个播客"""
    print(f"\n=== 测试获取播客 {podcast_id} ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/podcasts/{podcast_id}")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200


async def test_add_metric(podcast_id: int):
    """测试添加指标"""
    print(f"\n=== 测试添加指标 (播客 {podcast_id}) ===")
    async with httpx.AsyncClient() as client:
        data = {
            "snapshot_date": str(date.today()),
            "subscriber_count": 1000
        }
        response = await client.post(f"{BASE_URL}/api/podcasts/{podcast_id}/metrics", json=data)
        print(f"状态码: {response.status_code}")
        if response.status_code == 201:
            print(f"响应: {response.json()}")
            return True
        else:
            print(f"错误: {response.text}")
            return False


async def test_get_metrics(podcast_id: int):
    """测试获取指标"""
    print(f"\n=== 测试获取指标 (播客 {podcast_id}) ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/podcasts/{podcast_id}/metrics")
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"指标数量: {len(data)}")
        if data:
            print(f"最新指标: {data[0]}")
        return response.status_code == 200


async def run_tests():
    """运行所有测试"""
    print("开始 API 测试...")
    print("=" * 50)
    
    # 基础测试
    health_ok = await test_health_check()
    root_ok = await test_root()
    
    if not health_ok or not root_ok:
        print("\n❌ 基础测试失败，请检查服务是否正常运行")
        return
    
    # 播客 CRUD 测试
    podcast_id = await test_create_podcast()
    if podcast_id:
        await test_list_podcasts()
        await test_get_podcast(podcast_id)
        await test_add_metric(podcast_id)
        await test_get_metrics(podcast_id)
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print(f"\n可以访问 http://localhost:8000/docs 查看完整的 API 文档")


if __name__ == "__main__":
    asyncio.run(run_tests())

