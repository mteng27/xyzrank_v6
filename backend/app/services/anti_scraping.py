"""反爬虫策略模块

实现多种反爬虫策略，避免被目标网站封禁：
1. 请求频率控制（Rate Limiting）
2. User-Agent 轮换
3. 请求间隔随机化
4. 请求头随机化
5. 重试机制（指数退避）
6. 会话管理
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import deque
import time


class RateLimiter:
    """请求频率限制器
    
    使用令牌桶算法控制请求频率
    """
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()  # 存储请求时间戳
    
    async def acquire(self):
        """获取请求许可，如果超过限制则等待"""
        now = datetime.now()
        
        # 清理过期请求
        while self.requests and (now - self.requests[0]).total_seconds() > self.time_window:
            self.requests.popleft()
        
        # 如果超过限制，等待
        if len(self.requests) >= self.max_requests:
            oldest_request = self.requests[0]
            wait_time = self.time_window - (now - oldest_request).total_seconds() + 0.1
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # 重新清理
                now = datetime.now()
                while self.requests and (now - self.requests[0]).total_seconds() > self.time_window:
                    self.requests.popleft()
        
        # 记录本次请求
        self.requests.append(now)
    
    def get_wait_time(self) -> float:
        """计算需要等待的时间（秒）"""
        now = datetime.now()
        # 清理过期请求
        while self.requests and (now - self.requests[0]).total_seconds() > self.time_window:
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            oldest_request = self.requests[0]
            return self.time_window - (now - oldest_request).total_seconds() + 0.1
        return 0.0


class UserAgentRotator:
    """User-Agent 轮换器"""
    
    # 常见的浏览器 User-Agent 列表
    USER_AGENTS = [
        # Chrome (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        
        # Chrome (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Safari (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        
        # Firefox (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        
        # Firefox (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Edge (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    def __init__(self, user_agents: Optional[List[str]] = None):
        """
        Args:
            user_agents: 自定义 User-Agent 列表，如果为 None 则使用默认列表
        """
        self.user_agents = user_agents or self.USER_AGENTS
        self.current_index = 0
    
    def get_random(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(self.user_agents)
    
    def get_next(self) -> str:
        """获取下一个 User-Agent（轮换）"""
        ua = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return ua
    
    def get(self, strategy: str = "random") -> str:
        """
        获取 User-Agent
        
        Args:
            strategy: "random" 或 "rotate"
        """
        if strategy == "random":
            return self.get_random()
        else:
            return self.get_next()


class RequestHeaderGenerator:
    """请求头生成器
    
    生成随机的、真实的浏览器请求头
    """
    
    def __init__(self, user_agent_rotator: Optional[UserAgentRotator] = None):
        self.ua_rotator = user_agent_rotator or UserAgentRotator()
    
    def generate(self, strategy: str = "random") -> Dict[str, str]:
        """
        生成请求头
        
        Args:
            strategy: User-Agent 策略 ("random" 或 "rotate")
        
        Returns:
            请求头字典
        """
        user_agent = self.ua_rotator.get(strategy)
        
        # 根据 User-Agent 类型生成对应的请求头
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        # 如果是 Chrome，添加 Chrome 特有的请求头
        if "Chrome" in user_agent:
            headers["sec-ch-ua"] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = '"macOS"' if "Macintosh" in user_agent else '"Windows"'
        
        return headers


class RetryStrategy:
    """重试策略（指数退避）"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        """
        Args:
            max_attempts: 最大重试次数
            initial_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
            backoff_factor: 退避因子
            jitter: 是否添加随机抖动
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        计算第 attempt 次重试的延迟时间
        
        Args:
            attempt: 当前尝试次数（从1开始）
        
        Returns:
            延迟时间（秒）
        """
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # 添加 ±20% 的随机抖动
            jitter_amount = delay * 0.2
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)
        
        return delay


class RequestDelay:
    """请求延迟管理器
    
    在请求之间添加随机延迟，模拟人类行为
    """
    
    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        base_delay: float = 3.0
    ):
        """
        Args:
            min_delay: 最小延迟（秒）
            max_delay: 最大延迟（秒）
            base_delay: 基础延迟（秒），用于正态分布
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.base_delay = base_delay
    
    async def wait(self):
        """等待随机延迟时间"""
        # 使用正态分布生成更自然的延迟
        delay = random.normalvariate(self.base_delay, (self.max_delay - self.min_delay) / 4)
        delay = max(self.min_delay, min(delay, self.max_delay))
        await asyncio.sleep(delay)
        return delay
    
    def get_delay(self) -> float:
        """获取延迟时间（不等待）"""
        delay = random.normalvariate(self.base_delay, (self.max_delay - self.min_delay) / 4)
        return max(self.min_delay, min(delay, self.max_delay))


class AntiScrapingManager:
    """反爬虫管理器
    
    整合所有反爬虫策略
    """
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        user_agent_rotator: Optional[UserAgentRotator] = None,
        request_delay: Optional[RequestDelay] = None,
        retry_strategy: Optional[RetryStrategy] = None,
        header_generator: Optional[RequestHeaderGenerator] = None
    ):
        """
        Args:
            rate_limiter: 频率限制器
            user_agent_rotator: User-Agent 轮换器
            request_delay: 请求延迟管理器
            retry_strategy: 重试策略
            header_generator: 请求头生成器
        """
        self.rate_limiter = rate_limiter or RateLimiter(max_requests=10, time_window=60)
        self.user_agent_rotator = user_agent_rotator or UserAgentRotator()
        self.request_delay = request_delay or RequestDelay(min_delay=2.0, max_delay=5.0)
        self.retry_strategy = retry_strategy or RetryStrategy(max_attempts=3, initial_delay=1.0)
        self.header_generator = header_generator or RequestHeaderGenerator(self.user_agent_rotator)
    
    async def before_request(self):
        """请求前的准备工作"""
        # 1. 频率限制检查
        await self.rate_limiter.acquire()
        
        # 2. 随机延迟（模拟人类行为）
        await self.request_delay.wait()
    
    def get_headers(self, strategy: str = "random") -> Dict[str, str]:
        """获取请求头"""
        return self.header_generator.generate(strategy)
    
    async def retry_with_backoff(self, func, *args, **kwargs):
        """
        使用指数退避重试函数
        
        Args:
            func: 要重试的异步函数
            *args, **kwargs: 函数参数
        
        Returns:
            函数返回值
        
        Raises:
            最后一次尝试的异常
        """
        last_exception = None
        
        for attempt in range(1, self.retry_strategy.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_strategy.max_attempts:
                    delay = self.retry_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
        
        raise last_exception
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "rate_limiter": {
                "current_requests": len(self.rate_limiter.requests),
                "max_requests": self.rate_limiter.max_requests,
                "time_window": self.rate_limiter.time_window,
                "wait_time": self.rate_limiter.get_wait_time()
            },
            "user_agent": {
                "current_index": self.user_agent_rotator.current_index,
                "total_agents": len(self.user_agent_rotator.user_agents)
            }
        }


# 默认配置（保守策略，适合生产环境）
DEFAULT_ANTI_SCRAPING_CONFIG = {
    "rate_limiter": {
        "max_requests": 10,  # 每分钟最多10个请求
        "time_window": 60    # 60秒时间窗口
    },
    "request_delay": {
        "min_delay": 3.0,    # 最小延迟3秒
        "max_delay": 6.0,    # 最大延迟6秒
        "base_delay": 4.0    # 基础延迟4秒
    },
    "retry_strategy": {
        "max_attempts": 3,
        "initial_delay": 2.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}


def create_anti_scraping_manager(config: Optional[Dict] = None) -> AntiScrapingManager:
    """
    创建反爬虫管理器（使用配置）
    
    Args:
        config: 配置字典，如果为 None 则使用默认配置
    
    Returns:
        AntiScrapingManager 实例
    """
    if config is None:
        config = DEFAULT_ANTI_SCRAPING_CONFIG
    
    rate_limiter = RateLimiter(
        max_requests=config["rate_limiter"]["max_requests"],
        time_window=config["rate_limiter"]["time_window"]
    )
    
    request_delay = RequestDelay(
        min_delay=config["request_delay"]["min_delay"],
        max_delay=config["request_delay"]["max_delay"],
        base_delay=config["request_delay"]["base_delay"]
    )
    
    retry_strategy = RetryStrategy(
        max_attempts=config["retry_strategy"]["max_attempts"],
        initial_delay=config["retry_strategy"]["initial_delay"],
        max_delay=config["retry_strategy"]["max_delay"],
        backoff_factor=config["retry_strategy"]["backoff_factor"],
        jitter=config["retry_strategy"]["jitter"]
    )
    
    return AntiScrapingManager(
        rate_limiter=rate_limiter,
        request_delay=request_delay,
        retry_strategy=retry_strategy
    )


