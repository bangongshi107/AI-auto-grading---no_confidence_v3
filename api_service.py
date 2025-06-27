import os
import requests
import base64
import json
import time
import traceback
import configparser
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any, Tuple, Optional

TINY_BASE64_JPEG = "9j/4AAQSkZJRgABAQEAYABgAAD/9QAiRXhpZgAATU0AKgAAAAgAAQESAAMAAAABAAYAAAAAAAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVVWVhZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVVWVhZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLi5+Tl5ufo6ery8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD8QQKKKKAP/2Q=="

class ApiService:
    """
API服务类，负责调用各种AI API.
稳定支持 (大部分通过OpenAI兼容接口):
- OpenAI, Azure OpenAI, Moonshot, DeepSeek, 01.AI
- Aliyun (通义千问，通过OpenAI兼容模式)
- Volcengine (火山引擎方舟平台，OpenAI兼容，默认关闭深度思考)
- Zhipu (智谱GLM，OpenAI兼容)
- Baidu (百度AI Studio星河大模型 或 千帆ModelBuilder，均通过OpenAI兼容接口，用户需提供对应平台的API Key/Access Token)
- Tencent (腾讯混元，通过OpenAI兼容接口)
# ... (如果还有其他实验性API，保留其说明)
"""
    
    def __init__(self, config_manager):
        # 初始化所有API属性为空字符串 - 统一使用UI文件中的命名
        self.config_manager = config_manager
        self.session = requests.Session()  # 创建一个Session对象以复用连接
        self.current_question_index = None  # 当前题目索引
        self.first_api_successful_strategy = None # 缓存首次API调用成功的策略
        self.second_api_successful_strategy = None
        self.running = True  # 添加这一行

        self.specific_api_configs = {
            # 特定API的配置信息，用于驱动通用调用逻辑
            "openai": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False
            },
            "azure": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "api_key",
                "auth_header": "api-key",
                "url_needs_token": False
            },
            "baidu": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False,
                "status": "stable_openai_compatible"
            },
            "zhipu": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False,
                "status": "stable"
            },
            "aliyun": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False,
                "status": "stable_openai_compatible"
            },
            "volcengine": {
                "payload_template_type": "volcengine_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                # Base64编码的图片必须是带有前缀的Data URI格式, e.g., "data:image/jpeg;base64,<Base64编码>"
                "url_needs_token": False,
                "status": "stable"
            },
            "tencent": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False,
                "status": "stable_openai_compatible"
            },
            "moonshot": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False
            },
            "deepseek": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False
            },
            "01ai": {
                "payload_template_type": "openai_vision_v1",
                "auth_method": "bearer",
                "auth_header": "Authorization",
                "url_needs_token": False
            }
        }
    
    def update_config_from_manager(self):
        self.first_api_successful_strategy = None
        self.second_api_successful_strategy = None
        print("[API] ApiService 配置已更新，缓存的API调用策略已重置。")

    def set_current_question(self, question_index):
        self.current_question_index = question_index
        print(f"[API] 当前处理题目索引: {question_index}")
    
    def _detect_api_type(self, url: str) -> str:
        domain = url.lower()
        api_patterns = {
            "openai": ["openai.com", "api.openai", "openai.azure.com"],
            "azure": ["azure.com", "api.cognitive.microsoft", "openai.azure.com"],
            "baidu": ["baidu.com", "ernie", "wenxin", "aip.baidubce.com", "yiyan", "文心", "千帆"],
            "zhipu": ["zhipu", "chatglm", "bigmodel.cn", "智谱", "glm"],
            "aliyun": ["aliyun", "dashscope", "tongyi", "ecs.aliyuncs.com", "通义", "千问", "qwen"],
            "volcengine": ["volce", "volcengine", "ark.cn-beijing", "bytedance", "火山", "字节", "豆包"],
            "tencent": ["tencent", "hunyuan", "腾讯", "cloud.tencent.com", "混元"],
            "moonshot": ["moonshot", "月之暗面", "kimi"],
            "deepseek": ["deepseek", "深度求索"],
            "01ai": ["01.ai", "零一万物", "yi-"]
        }
        for provider, patterns in api_patterns.items():
            for pattern in patterns:
                if pattern in domain:
                    return provider
        if any(endpoint in url for endpoint in ["/v1/chat/completions", "/api/v1/chat/completions"]):
            return "openai_like"
        return "standard"

    def call_first_api(self, img_str, prompt):
        try:
            if not all([self.config_manager.first_api_key, self.config_manager.first_modelID, self.config_manager.first_api_url]):
                return None, "API配置不完整 (来自ConfigManager)"
            if self.first_api_successful_strategy:
                print("[API] 使用缓存的First API成功策略进行调用...")
                return self._execute_cached_strategy(self.first_api_successful_strategy, self.config_manager.first_api_key, self.config_manager.first_modelID, img_str, prompt)
            else:
                print("[API] 未找到缓存策略，执行首次First API调用和策略发现...")
                api_type = self._detect_api_type(self.config_manager.first_api_url)
                print(f"[API] 检测到API类型: {api_type}")
                result, error = self._call_api_with_adaptive_strategy(self.config_manager.first_api_url, self.config_manager.first_api_key, self.config_manager.first_modelID, img_str, prompt, api_type, api_group="first")
                if error:
                    error = self._get_user_friendly_error_message(error, api_type)
                return result, error
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"[API] 调用出错: {str(e)}\n{error_detail}")
            return None, f"API调用失败: {str(e)}"
    
    def call_second_api(self, img_str, prompt):
        try:
            if not all([self.config_manager.second_api_key, self.config_manager.second_modelID, self.config_manager.second_api_url]):
                return None, "API配置不完整"
            if self.second_api_successful_strategy:
                print("[API] 使用缓存的Second API成功策略进行调用...")
                return self._execute_cached_strategy(self.second_api_successful_strategy, self.config_manager.second_api_key, self.config_manager.second_modelID, img_str, prompt)
            else:
                print("[API] 未找到缓存策略，执行首次Second API调用和策略发现...")
                api_type = self._detect_api_type(self.config_manager.second_api_url)
                print(f"[API] 检测到API类型: {api_type}")
                result, error = self._call_api_with_adaptive_strategy(self.config_manager.second_api_url, self.config_manager.second_api_key, self.config_manager.second_modelID, img_str, prompt, api_type, api_group="second")
                if error:
                    error = self._get_user_friendly_error_message(error, api_type)
                return result, error
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"[API] 调用出错: {str(e)}\n{error_detail}")
            return None, f"API调用失败: {str(e)}"
    
    def _standardize_api_endpoint(self, url: str, api_type: str) -> list:
        cleaned_url = url.strip().rstrip('/')
        generic_suffix = "/chat/completions"
        standard_openai_suffix = "/v1/chat/completions"
        candidates = [cleaned_url]
        if not cleaned_url.endswith(generic_suffix):
            if api_type in ["baidu", "aliyun", "volcengine"]:
                 candidates.append(f"{cleaned_url}{generic_suffix}")
            else:
                candidates.append(f"{cleaned_url}{standard_openai_suffix}")
        final_candidates = []
        for c in candidates:
            if c not in final_candidates:
                final_candidates.append(c)
        return final_candidates

    def _call_api_with_adaptive_strategy(self, api_url: str, api_key: str, model_id: str, img_str: str, prompt: str, api_type: str, api_group: str):
        url_candidates = self._standardize_api_endpoint(api_url, api_type)
        print(f"[API] (优化策略) API类型: {api_type}, URL候选列表: {url_candidates}")
        api_config = self.specific_api_configs.get(api_type, {})
        payload_template_type = api_config.get("payload_template_type", "openai_vision_v1")
        print(f"[API] (优化策略) 使用的Payload模板: {payload_template_type}")

        headers = {"Content-Type": "application/json"}
        if api_config.get("extra_headers"):
            headers.update(api_config.get("extra_headers"))
        auth_method = api_config.get("auth_method", "bearer")
        auth_header_name = api_config.get("auth_header", "Authorization")

        if auth_method == "bearer":
            headers[auth_header_name] = f"Bearer {api_key}"
        elif auth_method == "api_key":
            headers[auth_header_name] = api_key

        for test_url in url_candidates:
            if not self.running:
                return None, "线程已停止"

            # 步骤1: 默认使用 data_uri 格式尝试
            image_format = "data_uri"
            print(f"[API] (优化策略) 尝试URL: {test_url}, 默认图片格式: {image_format}")
            
            temp_api_config = api_config.copy()
            temp_api_config["image_url_format"] = image_format
            payload = self._build_payload_from_template(payload_template_type, model_id, img_str, prompt, temp_api_config)
            
            if not payload:
                print(f"[API] 警告: 为API类型 '{api_type}' 构建请求体失败 (图片格式: {image_format})")
                continue

            try:
                response = self._robust_api_call(test_url, headers, payload, max_retries=1)
                if response is None:
                    print(f"[API] 请求失败，无响应 (URL: {test_url})")
                    break # URL不通，无需尝试其他格式，直接换下一个URL

                # 步骤2: 处理响应
                if response.status_code == 200:
                    # 调用成功，处理并返回结果
                    result_data = response.json()
                    content = self._extract_response_content(result_data)
                    if content and len(content) > 10:
                        print(f"[API] (优化策略) 调用成功！URL: {test_url}, 图片格式: {image_format}")
                        # 缓存成功策略
                        final_api_config = temp_api_config.copy()
                        def successful_payload_builder(m_id, i_str, p_str):
                            return self._build_payload_from_template(payload_template_type, m_id, i_str, p_str, final_api_config)
                        strategy_to_cache = {
                            "type": "unified_adaptive", "api_type_used": api_type, "successful_url": test_url,
                            "payload_builder": successful_payload_builder, "auth_method": auth_method,
                            "auth_header": auth_header_name, "extra_headers": api_config.get("extra_headers")
                        }
                        if api_group == "first": self.first_api_successful_strategy = strategy_to_cache
                        elif api_group == "second": self.second_api_successful_strategy = strategy_to_cache
                        print(f"[API] (优化策略) 已缓存 {api_group} API 的成功策略。")
                        return content, None
                    else:
                        print(f"[API] 响应内容为空或过短: {content}")
                        # 内容问题，但请求成功，不再回退，继续下一个URL
                        continue

                elif response.status_code == 400 and img_str: # 仅在有图片时，400才可能与格式有关
                    # 步骤3: 触发回退机制
                    print(f"[API] (优化策略) 收到400错误，回退尝试 pure_base64 格式。")
                    image_format_fallback = "pure_base64"
                    
                    temp_api_config_fallback = api_config.copy()
                    temp_api_config_fallback["image_url_format"] = image_format_fallback
                    payload_fallback = self._build_payload_from_template(payload_template_type, model_id, img_str, prompt, temp_api_config_fallback)

                    response_fallback = self._robust_api_call(test_url, headers, payload_fallback, max_retries=1)
                    if response_fallback and response_fallback.status_code == 200:
                        result_data_fallback = response_fallback.json()
                        content_fallback = self._extract_response_content(result_data_fallback)
                        if content_fallback and len(content_fallback) > 10:
                            print(f"[API] (优化策略) 回退调用成功！URL: {test_url}, 图片格式: {image_format_fallback}")
                            # 缓存成功的回退策略
                            final_api_config = temp_api_config_fallback.copy()
                            def successful_payload_builder(m_id, i_str, p_str):
                                return self._build_payload_from_template(payload_template_type, m_id, i_str, p_str, final_api_config)
                            strategy_to_cache = {
                                "type": "unified_adaptive", "api_type_used": api_type, "successful_url": test_url,
                                "payload_builder": successful_payload_builder, "auth_method": auth_method,
                                "auth_header": auth_header_name, "extra_headers": api_config.get("extra_headers")
                            }
                            if api_group == "first": self.first_api_successful_strategy = strategy_to_cache
                            elif api_group == "second": self.second_api_successful_strategy = strategy_to_cache
                            print(f"[API] (优化策略) 已缓存 {api_group} API 的成功回退策略。")
                            return content_fallback, None
                    # 如果回退也失败，则记录日志，然后让循环继续到下一个URL
                    print(f"[API] (优化策略) 回退尝试 pure_base64 格式失败。")

                elif response.status_code == 404:
                    print(f"[API] 端点不存在 (404)，此URL无效，尝试下一个URL。")
                    break # 跳出循环，直接尝试下一个URL
                else:
                    # 其他错误，不触发回退
                    error_msg = f"API调用失败 (URL: {test_url}), 状态码: {response.status_code}, 响应: {response.text[:150]}"
                    print(f"[API] {error_msg}")
                    # 对于其他错误(如401, 403)，直接尝试下一个URL
                    continue

            except requests.exceptions.RequestException as e:
                print(f"[API] 请求异常 (URL: {test_url}): {e}")
                break # 请求异常通常是URL问题，跳到下一个URL

        return None, f"所有URL和图片格式组合均失败 (API类型: {api_type})"

    def _extract_response_content(self, response_data: dict) -> str:
        extraction_paths = [
            lambda d: d.get("choices", [{}])[0].get("message", {}).get("content"),
            lambda d: d.get("choices", [{}])[0].get("text"),
            lambda d: d.get("Response", {}).get("Choices", [{}])[0].get("Message", {}).get("Content"),
            lambda d: d.get("result"), lambda d: d.get("answer"), lambda d: d.get("response"), lambda d: d.get("content"),
            lambda d: d.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content"),
            lambda d: d.get("output", {}).get("text"),
            lambda d: d.get("data", {}).get("content"), lambda d: d.get("data", {}).get("text"),
            lambda d: d.get("data", [{}])[0].get("content") if isinstance(d.get("data"), list) else None,
            lambda d: d.get("message"), lambda d: d.get("text"), lambda d: d.get("generated_text"),
        ]
        for extractor in extraction_paths:
            try:
                content = extractor(response_data)
                if content and isinstance(content, str) and content.strip():
                    return content.strip()
            except (KeyError, IndexError, TypeError, AttributeError):
                continue
        return str(response_data)

    def _robust_api_call(self, url, headers, payload, max_retries=3):
        for attempt in range(max_retries):
            try:
                timeout = 30 + (attempt * 15)
                print(f"[API] 第 {attempt + 1} 次尝试，超时时间: {timeout}s")
                response = self.session.post(url, headers=headers, json=payload, timeout=timeout, verify=True)
                if response.status_code == 200:
                    return response
                elif response.status_code in [429, 502, 503, 504]:
                    wait_time = (attempt + 1) * 2
                    print(f"[API] 状态码 {response.status_code}，等待 {wait_time}s 后重试")
                    time.sleep(wait_time)
                    continue
                else:
                    return response
            except requests.exceptions.Timeout:
                print(f"[API] 第 {attempt + 1} 次尝试超时")
                if attempt < max_retries - 1:
                    time.sleep(2)
            except requests.exceptions.ConnectionError as e:
                print(f"[API] 连接错误: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"[API] 其他错误: {str(e)}")
                break
        return None

    def _get_user_friendly_error_message(self, error_msg: str, api_type: str) -> str:
        error_solutions = {
            "404": {"default": "API端点不存在，请检查URL是否正确"},
            "401": {"default": "API密钥无效或已过期，请检查密钥是否正确"},
            "403": {"default": "API访问被拒绝，请检查密钥权限或账户余额"},
            "429": {"default": "API调用频率过高，请稍后重试"},
            "500": {"default": "API服务器内部错误，请稍后重试"}
        }
        status_code = None
        for code in error_solutions:
            if code in error_msg:
                status_code = code
                break
        if status_code:
            return f"{error_msg}\n\n💡 建议: {error_solutions[status_code].get(api_type, error_solutions[status_code]['default'])}"
        return error_msg
    
    def _execute_cached_strategy(self, strategy: dict, api_key: str, model_id: str, img_str: str, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            successful_url = strategy.get("successful_url")
            payload_builder = strategy.get("payload_builder")
            if not successful_url or not payload_builder:
                print("[API] 缓存策略无效: 缺少URL或payload_builder")
                if strategy is self.first_api_successful_strategy: self.first_api_successful_strategy = None
                elif strategy is self.second_api_successful_strategy: self.second_api_successful_strategy = None
                return None, "缓存策略无效"
            new_payload = payload_builder(model_id, img_str, prompt)
            headers = {"Content-Type": "application/json"}
            if strategy.get("extra_headers"): headers.update(strategy.get("extra_headers"))
            auth_method = strategy.get("auth_method")
            auth_header_name = strategy.get("auth_header")
            if auth_method == "bearer" and auth_header_name:
                headers[auth_header_name] = f"Bearer {api_key}"
            elif auth_method == "api_key" and auth_header_name:
                headers[auth_header_name] = api_key
            print(f"[API] 执行缓存策略: 类型={strategy.get('api_type_used', 'Unknown')}, URL={successful_url}, AuthMethod={auth_method}")
            response = self._robust_api_call(successful_url, headers, new_payload, max_retries=1)
            if response is None:
                if strategy is self.first_api_successful_strategy: self.first_api_successful_strategy = None
                elif strategy is self.second_api_successful_strategy: self.second_api_successful_strategy = None
                return None, "API请求失败，无响应"
            if response.status_code == 200:
                content = self._extract_response_content(response.json())
                if content and len(content) > 10:
                    return content, None
                error_msg = "API响应内容为空或过短"
            else:
                error_msg = f"API调用失败，状态码: {response.status_code}, 响应: {response.text[:100]}"
            if strategy is self.first_api_successful_strategy: self.first_api_successful_strategy = None
            elif strategy is self.second_api_successful_strategy: self.second_api_successful_strategy = None
            return None, error_msg
        except Exception as e:
            if strategy is self.first_api_successful_strategy: self.first_api_successful_strategy = None
            elif strategy is self.second_api_successful_strategy: self.second_api_successful_strategy = None
            return None, f"执行缓存策略时发生异常: {str(e)}"

    def test_api_connection(self, api_type="first"):
        try:
            if api_type == "first":
                if not all([self.config_manager.first_api_key, self.config_manager.first_modelID, self.config_manager.first_api_url]):
                    return False, "第一组API配置不完整"
                api_url, api_key, model_id = self.config_manager.first_api_url, self.config_manager.first_api_key, self.config_manager.first_modelID
                group_name = "第一组"
            elif api_type == "second":
                if not all([self.config_manager.second_api_key, self.config_manager.second_modelID, self.config_manager.second_api_url]):
                    return False, "第二组API配置不完整"
                api_url, api_key, model_id = self.config_manager.second_api_url, self.config_manager.second_api_key, self.config_manager.second_modelID
                group_name = "第二组"
            else:
                return False, "无效的API类型进行测试"
            
            detected_type = self._detect_api_type(api_url)
            print(f"[API Test] 测试{group_name}API，检测类型: {detected_type}, URL: {api_url}")
            
            # 永久修改为纯文本测试
            test_prompt = "你好"
            test_img_str = "" # 传递空字符串表示无图片
            
            result, error = self._call_api_with_adaptive_strategy(api_url, api_key, model_id, test_img_str, test_prompt, detected_type, api_type)
            
            if result and not error:
                return True, f"{group_name}API连接成功 (检测类型: {detected_type})"
            else:
                # 增强错误提示，为所有测试失败的情况增加通用建议
                enhanced_error = f"{group_name}API连接失败 (检测类型: {detected_type}): {error}"
                suggestion = "\n\n💡 请检查您输入的API URL、Key、ID。必须使用视觉模型，确保账户余额充足。"
                return False, enhanced_error + suggestion
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"[API Test] API测试过程中发生异常: {str(e)}\n{error_detail}")
            return False, f"API测试异常: {str(e)}"

    def _build_payload_from_template(self, template_type: str, model_id: str, img_str: str, prompt: str, api_config: dict) -> dict:
        clean_prompt = prompt.strip()
        
        # 如果没有图片，则发送纯文本请求
        if not img_str:
            return {
                "model": model_id,
                "messages": [{"role": "user", "content": clean_prompt}],
                "max_tokens": 4000, "stream": False
            }

        # --- 以下是处理图片请求的逻辑 ---
        base64_marker = "base64,"
        marker_pos = img_str.find(base64_marker)
        if marker_pos != -1:
            pure_base64_str = img_str[marker_pos + len(base64_marker):]
        else:
            pure_base64_str = img_str
        
        image_url_format = api_config.get("image_url_format", "data_uri")
        if image_url_format == "pure_base64":
            url_content = pure_base64_str
        else:
            url_content = f"data:image/jpeg;base64,{pure_base64_str}"

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        # 遵循官方文档建议，图片在前，文本在后
                        {"type": "image_url", "image_url": {"url": url_content}},
                        {"type": "text", "text": clean_prompt}
                    ]
                }
            ],
            "max_tokens": 4000,
            "stream": False
        }
        if template_type == "volcengine_vision_v1":
            payload["thinking"] = {"type": "disabled"}
            payload["max_tokens"] = 4096
        return payload
