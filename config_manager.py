import configparser
import os
import json
import logging
import sys # 新增导入
import appdirs # 新增导入

class MissingCriticalConfigError(ValueError):
    """自定义异常，用于表示关键配置项缺失或无效。"""
    pass

class ConfigManager:
    """配置管理器,负责保存和加载配置"""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if ConfigManager._initialized:
            return
        self.parser = configparser.ConfigParser(allow_no_value=True)
        
        app_name = "AutoGraderApp" # 定义您的应用名称
        app_author = "Mr.Why" # 定义应用作者或公司名（可选但推荐）

        if getattr(sys, 'frozen', False):
            # 打包后的exe，配置文件存储在用户配置目录
            self.config_dir = appdirs.user_config_dir(app_name, app_author)
        else:
            # 开发时，配置文件仍在项目下的 setting 目录
            self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setting")
        
        self.config_file_path = os.path.join(self.config_dir, "config.ini")
        
        os.makedirs(self.config_dir, exist_ok=True) # 确保目录存在
        
        self.max_questions = 4
        self._init_default_config()
        self.load_config()
        ConfigManager._initialized = True

    def _init_default_config(self):
        """初始化默认配置值（允许为空）"""
        # API配置 - 允许为空
        self.first_api_key = ""
        self.first_modelID = ""
        self.first_api_url = ""
        self.second_api_key = ""
        self.second_modelID = ""
        self.second_api_url = ""
        
        # 双评配置
        self.dual_evaluation_enabled = False
        self.score_diff_threshold = 5
        
        # UI配置 - 允许为空
        self.subject = ""
        
        # 自动化配置 - 设置合理默认值
        self.cycle_number = 1
        self.wait_time = 1
        
        # 位置配置 - 已移除全局翻页按钮位置
        pass
        
        # 题目配置 - 初始化为禁用状态
        self.question_configs = {}
        for i in range(1, self.max_questions + 1):
            self.question_configs[str(i)] = {
                'enabled': False, # 对于第一题，初始时可以考虑为 True，但UI会加载实际配置
                'score_input_pos': None,
                'confirm_button_pos': None,
                'standard_answer': "",
                'answer_area': None,
                'min_score': 0,
                'max_score': 100,
            'enable_next_button': False,
            'next_button_pos': None,
            'question_type': 'Subjective_PointBased_QA', # <--- 新增默认题目类型
        }
        if i == 1: # 仅为第一题添加三步打分相关默认配置
                self.question_configs[str(i)].update({
                    'enable_three_step_scoring': False,
                    'score_input_pos_step1': None,
                    'score_input_pos_step2': None,
                    'score_input_pos_step3': None
                })

    def load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        if not os.path.exists(self.config_file_path):
            print(f"配置文件不存在，创建默认配置: {self.config_file_path}")
            self._save_config_to_file()
            return

        try:
            read_ok = self.parser.read(self.config_file_path, encoding='utf-8')
            if not read_ok:
                print(f"无法读取配置文件，使用默认配置")
                return
        except configparser.Error as e:
            print(f"配置文件格式错误，使用默认配置: {e}")
            return

        # 安全地读取配置，不存在则使用默认值
        self._safe_load_config()

    def _safe_load_config(self):
        """安全地加载配置，缺失项使用默认值"""
        # API配置
        self.first_api_key = self._get_config_safe('API', 'first_api_key', "")
        self.first_modelID = self._get_config_safe('API', 'first_modelID', "")
        self.first_api_url = self._get_config_safe('API', 'first_api_url', "")
        self.second_api_key = self._get_config_safe('API', 'second_api_key', "")
        self.second_modelID = self._get_config_safe('API', 'second_modelID', "")
        self.second_api_url = self._get_config_safe('API', 'second_api_url', "")
        
        # 双评配置
        self.dual_evaluation_enabled = self._get_config_safe('DualEvaluation', 'enabled', False, bool)
        self.score_diff_threshold = self._get_config_safe('DualEvaluation', 'score_diff_threshold', 5, int)
        
        # UI配置
        self.subject = self._get_config_safe('UI', 'subject', "")
        
        # 自动化配置
        self.cycle_number = self._get_config_safe('Auto', 'cycle_number', 1, int)
        self.wait_time = self._get_config_safe('Auto', 'wait_time', 1, int)
        
        # 位置配置 - 已移除全局翻页按钮位置
        pass
        
        # 题目配置
        for i in range(1, self.max_questions + 1):
            section_name = f'Question{i}'
            q_idx_str = str(i)
            
            current_q_config = { # 使用一个临时字典来构建当前题目的配置
                'enabled': self._get_config_safe(section_name, 'enabled', False, bool),
                'score_input_pos': self._parse_position(self._get_config_safe(section_name, 'score_input', None)),
                'confirm_button_pos': self._parse_position(self._get_config_safe(section_name, 'confirm_button', None)),
                'standard_answer': self._get_config_safe(section_name, 'standard_answer', ""),
                'answer_area': self._parse_area(self._get_config_safe(section_name, 'answer_area', None)),
                'min_score': self._get_config_safe(section_name, 'min_score', 0, int),
                'max_score': self._get_config_safe(section_name, 'max_score', 100, int),
                'enable_next_button': self._get_config_safe(section_name, 'enable_next_button', False, bool),
                'next_button_pos': self._parse_position(self._get_config_safe(section_name, 'next_button_pos', None)),
                'question_type': self._get_config_safe(section_name, 'question_type', 'Subjective_PointBased_QA', str) # 新增加载
            }

            if i == 1: # 仅为第一题加载三步打分相关配置
                current_q_config['enable_three_step_scoring'] = self._get_config_safe(section_name, 'enable_three_step_scoring', False, bool)
                current_q_config['score_input_pos_step1'] = self._parse_position(self._get_config_safe(section_name, 'score_input_pos_step1', None))
                current_q_config['score_input_pos_step2'] = self._parse_position(self._get_config_safe(section_name, 'score_input_pos_step2', None))
                current_q_config['score_input_pos_step3'] = self._parse_position(self._get_config_safe(section_name, 'score_input_pos_step3', None))
            
            self.question_configs[q_idx_str] = current_q_config

        # --- 强制确保第一题始终启用 ---
        if '1' in self.question_configs:
            if not self.question_configs['1'].get('enabled', False): # 如果未启用或enabled键不存在
                self.question_configs['1']['enabled'] = True
                # 可以选择性地记录一个日志或打印一个消息，表明进行了强制修正
                print("ConfigManager Info: Question 1 'enabled' state was found as false or missing, "
                      "and has been forcibly set to true during config load.")
        else:
            # 理论上不应该发生，因为 _init_default_config 会创建 '1'
            print("ConfigManager Warning: Question 1 config not found after loading, "
                  "cannot enforce 'enabled' state.")
        # --- 结束强制设置 ---

    def _get_config_safe(self, section, option, default_value, value_type=str):
        """安全地获取配置值，不存在则返回默认值"""
        try:
            if not self.parser.has_section(section) or not self.parser.has_option(section, option):
                return default_value
            
            raw_val = self.parser.get(section, option)
            
            if value_type == str:
                return raw_val
            elif value_type == int:
                return int(raw_val) if raw_val.strip() else default_value
            elif value_type == bool:
                return self.parser.getboolean(section, option)
            else:
                return default_value
        except (ValueError, TypeError):
            return default_value

    def _parse_position(self, pos_str):
        """解析位置字符串为坐标元组"""
        try:
            if not pos_str or not pos_str.strip():
                return None
            x, y = map(str.strip, pos_str.split(','))
            return (int(x), int(y))
        except (ValueError, AttributeError, TypeError):
            return None

    def _parse_area(self, area_str):
        """解析区域字符串为坐标字典"""
        try:
            if not area_str or not area_str.strip():
                return None
            coords = [int(c.strip()) for c in area_str.split(',')]
            if len(coords) != 4:
                return None
            return {'x1': coords[0], 'y1': coords[1], 'x2': coords[2], 'y2': coords[3]}
        except (ValueError, TypeError):
            return None

    def update_config_in_memory(self, field_name, value): # <--- 名称改变
        """更新内存中的配置项。"""
        try:
            self._update_memory_config(field_name, value)
            # print(f"ConfigManager: Memory updated for {field_name} = {value}") # 可选的调试打印
        except Exception as e:
            # 考虑是否需要更强的错误处理，或者仅记录
            print(f"ConfigManager: Error updating memory for {field_name}: {e}")
            # 根据需要，这里可以重新抛出异常或记录到日志系统

    def _update_memory_config(self, field_name, value):
        """更新内存中的配置"""
        if field_name == 'first_api_key':
            self.first_api_key = str(value) if value is not None else ""
        elif field_name == 'first_modelID':
            self.first_modelID = str(value) if value is not None else ""
        elif field_name == 'first_api_url':
            self.first_api_url = str(value) if value is not None else ""
        elif field_name == 'second_api_key':
            self.second_api_key = str(value) if value is not None else ""
        elif field_name == 'second_modelID':
            self.second_modelID = str(value) if value is not None else ""
        elif field_name == 'second_api_url':
            self.second_api_url = str(value) if value is not None else ""
        elif field_name == 'subject':
            self.subject = str(value) if value is not None else ""
        elif field_name == 'cycle_number':
            self.cycle_number = max(1, int(value)) if value is not None else 1
        elif field_name == 'wait_time':
            self.wait_time = max(1, int(value)) if value is not None else 1
        elif field_name == 'dual_evaluation_enabled':
            self.dual_evaluation_enabled = bool(value) if value is not None else False
        elif field_name == 'score_diff_threshold':
            self.score_diff_threshold = max(1, int(value)) if value is not None else 5
        elif field_name.startswith('question_'):
            self._update_question_config(field_name, value)
        else:
            raise ValueError(f"未知的配置字段: {field_name}")

    def _update_question_config(self, field_name, value):
        """更新题目相关配置"""
        parts = field_name.split('_')
        if len(parts) < 3:
            return
        
        question_index = parts[1]
        field_type = '_'.join(parts[2:])
        
        if question_index not in self.question_configs:
            return
        
        if field_type == 'enabled':
            self.question_configs[question_index]['enabled'] = bool(value) if value is not None else False
        elif field_type == 'standard_answer':
            self.question_configs[question_index]['standard_answer'] = str(value) if value is not None else ""
        elif field_type == 'score_input_pos':
            self.question_configs[question_index]['score_input_pos'] = value
        elif field_type == 'confirm_button_pos':
            self.question_configs[question_index]['confirm_button_pos'] = value
        elif field_type == 'answer_area':
            self.question_configs[question_index]['answer_area'] = value
        elif field_type == 'min_score':
            self.question_configs[question_index]['min_score'] = int(value) if value is not None else 0
        elif field_type == 'max_score':
            self.question_configs[question_index]['max_score'] = int(value) if value is not None else 100
        elif field_type == 'enable_next_button':
            self.question_configs[question_index]['enable_next_button'] = bool(value) if value is not None else False
        elif field_type == 'next_button_pos':
            self.question_configs[question_index]['next_button_pos'] = value  # value应该是(x,y)元组或None
        elif field_type == 'enable_three_step_scoring': # 新增
            if question_index == '1': # 确保只对第一题操作
                self.question_configs[question_index]['enable_three_step_scoring'] = bool(value) if value is not None else False
        elif field_type == 'score_input_pos_step1': # 新增
            if question_index == '1':
                self.question_configs[question_index]['score_input_pos_step1'] = value
        elif field_type == 'score_input_pos_step2': # 新增
            if question_index == '1':
                self.question_configs[question_index]['score_input_pos_step2'] = value
        elif field_type == 'score_input_pos_step3': # 新增
            if question_index == '1':
                self.question_configs[question_index]['score_input_pos_step3'] = value
        elif field_type == 'question_type': # <--- 新增处理
            self.question_configs[question_index]['question_type'] = str(value) if value is not None else 'Subjective_PointBased_QA'

    def update_question_config(self, question_index, field_type, value):
        """
        更新指定题目的单个配置项。
        这是一个公共方法，用于从外部（如UI）更新题目配置。
        """
        # 构造 field_name 以匹配 _update_memory_config 的逻辑
        field_name = f"question_{question_index}_{field_type}"
        self._update_memory_config(field_name, value)

    def save_all_configs_to_file(self):
        """
        将 ConfigManager 内存中的所有当前配置保存到 config.ini 文件。
        返回 True 表示成功，False 表示失败。
        """
        # 你可以添加一些日志打印，方便调试
        # print("ConfigManager: Attempting to save all configs to file via save_all_configs_to_file()...")
        success = self._save_config_to_file()
        # if success:
        #     print("ConfigManager: All configs saved to file successfully.")
        # else:
        #     print("ConfigManager: Failed to save all configs to file.")
        return success

    def _save_config_to_file(self):
        """将内存中的配置保存到文件"""
        try:
            config = configparser.ConfigParser()
            
            # API配置
            config['API'] = {
                'first_api_key': self.first_api_key,
                'first_modelID': self.first_modelID,
                'first_api_url': self.first_api_url,
                'second_api_key': self.second_api_key,
                'second_modelID': self.second_modelID,
                'second_api_url': self.second_api_url
            }
            
            # UI配置
            config['UI'] = {
                'subject': self.subject
            }
            
            # 自动化配置
            config['Auto'] = {
                'cycle_number': str(self.cycle_number),
                'wait_time': str(self.wait_time)
            }
            
            # 双评配置
            config['DualEvaluation'] = {
                'enabled': str(self.dual_evaluation_enabled).lower(),
                'score_diff_threshold': str(self.score_diff_threshold)
            }
            
            # 位置配置 - 已移除全局翻页按钮位置
            # config['Position'] = {}  # 如果未来有其他全局位置信息，可以取消注释
            
            # 题目配置
            for i in range(1, self.max_questions + 1):
                section_name = f'Question{i}'
                q_idx_str = str(i)
                q_config = self.question_configs[q_idx_str]
                
                # --- 强制第一题的 enabled 状态为 true ---
                is_enabled_for_saving = q_config['enabled']
                if q_idx_str == '1':
                    is_enabled_for_saving = True
                # --- 结束强制设置 ---

                section_data = {
                    'enabled': str(is_enabled_for_saving).lower(), # <--- 使用 is_enabled_for_saving
                    'standard_answer': q_config['standard_answer'],
                    'min_score': str(q_config['min_score']),
                    'max_score': str(q_config['max_score']),
                    'enable_next_button': str(q_config['enable_next_button']).lower(),
                    'question_type': q_config.get('question_type', 'Subjective_PointBased_QA') # <--- 新增保存
                }
                
                # 只保存非空的位置配置
                if q_config['next_button_pos'] is not None:
                    section_data['next_button_pos'] = f"{q_config['next_button_pos'][0]},{q_config['next_button_pos'][1]}"
                else:
                    section_data['next_button_pos'] = ""
                if q_config['score_input_pos'] is not None:
                    section_data['score_input'] = f"{q_config['score_input_pos'][0]},{q_config['score_input_pos'][1]}"
                
                if q_config['confirm_button_pos'] is not None:
                    section_data['confirm_button'] = f"{q_config['confirm_button_pos'][0]},{q_config['confirm_button_pos'][1]}"
                
                if q_config['answer_area'] is not None:
                    area = q_config['answer_area']
                    section_data['answer_area'] = f"{area['x1']},{area['y1']},{area['x2']},{area['y2']}"
                else:
                    section_data['answer_area'] = ""
                


                if q_idx_str == '1': # 仅为第一题保存三步打分相关配置
                    section_data['enable_three_step_scoring'] = str(q_config.get('enable_three_step_scoring', False)).lower()
                    
                    pos_step1 = q_config.get('score_input_pos_step1')
                    section_data['score_input_pos_step1'] = f"{pos_step1[0]},{pos_step1[1]}" if pos_step1 else ""
                    
                    pos_step2 = q_config.get('score_input_pos_step2')
                    section_data['score_input_pos_step2'] = f"{pos_step2[0]},{pos_step2[1]}" if pos_step2 else ""
                    
                    pos_step3 = q_config.get('score_input_pos_step3')
                    section_data['score_input_pos_step3'] = f"{pos_step3[0]},{pos_step3[1]}" if pos_step3 else ""

                config[section_name] = section_data
            
            # 保存到文件
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def validate_for_operation(self):
        """验证当前配置是否满足操作要求（按需验证）"""
        errors = []
        
        # 验证第一组API配置
        if not self.first_api_key.strip():
            errors.append("第一个API密钥不能为空")
        if not self.first_modelID.strip():
            errors.append("第一个模型ID不能为空")
        if not self.first_api_url.strip():
            errors.append("第一个API地址不能为空")
        
        # 验证双评配置（如果启用）
        if self.dual_evaluation_enabled:
            if not self.second_api_key.strip():
                errors.append("启用双评时，第二个API密钥不能为空")
            if not self.second_modelID.strip():
                errors.append("启用双评时，第二个模型ID不能为空")
            if not self.second_api_url.strip():
                errors.append("启用双评时，第二个API地址不能为空")
        
        # 验证启用的题目配置
        enabled_questions = self.get_enabled_questions()
        if not enabled_questions:
            errors.append("至少需要启用一道题目")
        
        for q_index in enabled_questions:
            q_config = self.question_configs[str(q_index)]
            
            if not q_config['standard_answer'].strip():
                errors.append(f"第{q_index}题的标准答案不能为空")
            
            
            if q_config['score_input_pos'] is None:
                errors.append(f"第{q_index}题的分数输入位置未设置")
            
            if q_config['confirm_button_pos'] is None:
                errors.append(f"第{q_index}题的确认按钮位置未设置")
            
            if q_config['answer_area'] is None:
                errors.append(f"第{q_index}题的答案区域未设置")
        
        return len(errors) == 0, errors

    def get_enabled_questions(self):
        """获取所有启用的题目索引列表"""
        return [i for i in range(1, self.max_questions + 1) 
                if self.question_configs[str(i)]['enabled']]

    def get_question_config(self, question_index):
        """获取指定题目的配置"""
        return self.question_configs.get(str(question_index), {'enabled': False})
