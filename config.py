import os
import logging

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

KNOWLEDGE_DIR = os.path.join(PROJECT_ROOT, "knowledge")

TEMPLATE_DIR = os.path.join(KNOWLEDGE_DIR, "templates")

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

SCHEMA_DIR = os.path.join(KNOWLEDGE_DIR, "schemas")

PLATFORM_API_URL = "http://127.0.0.1:8561"

OLLAMA_BASE_URL = "http://localhost:11434"

OLLAMA_MODEL = "qwen2.5:7b"

LLM_API_TYPE = os.environ.get("LLM_API_TYPE", "ollama")

LLM_API_URL = os.environ.get("LLM_API_URL", OLLAMA_BASE_URL)

LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", OLLAMA_MODEL)

LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "30"))

LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4096"))

MODELING_TYPE_MAP = {
    "试卡行为分析": ["试卡", "小额测试", "试探", "小额试探", "小额试卡"],
    "沉寂卡分析": ["沉寂", "休眠", "长期不动", "沉寂卡", "休眠卡"],
    "消费账户分析": ["消费", "购物", "支出", "消费痕迹", "消费账户"],
    "同IP/MAC分析": ["同ip", "同mac", "网络", "设备", "ip", "mac", "同ip和mac", "ip和mac"],
    "调单层级分析": ["调单", "层级", "上下级", "层级分析", "调单层级"],
    "资金快进快出": ["快进快出", "过桥", "过渡", "快进", "快出", "过桥账户"],
    "资金特征分析": ["资金特征", "交易特征", "异常交易", "特征分析"],
    "账户存活度分析": ["存活度", "活跃度", "使用频率", "存活", "活跃账户"],
    "手机号提取": ["手机号", "电话", "联系方式", "提取手机号", "疑似手机号"],
    "账户信息查询": ["账户信息", "开户信息", "基本信息", "信息查询", "信息类型"],
    "同住人员分析": ["同住", "同地址", "住宿", "同住人员"],
    "资金万能表": ["万能", "综合", "全量", "身份证", "万能表"],
}

DATA_SOURCE_TABLES = {
    "tt.jz_bank_bill": {
        "name": "银行交易流水表",
        "description": "存储银行交易流水明细数据",
    },
    "tt.jz_bank_zh": {
        "name": "银行账户表",
        "description": "存储银行账户基本信息",
    },
    "tt.jz_bank_zhxx": {
        "name": "账户信息类型表",
        "description": "存储账户扩展信息及类型",
    },
}

LOG_LEVEL = logging.INFO

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

PLATFORM_USERNAME = "admin"

PLATFORM_PASSWORD = "admin"

OLLAMA_TIMEOUT = 30


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(LOG_DIR, "ai_engine.log"), encoding="utf-8"
            ),
        ],
    )
