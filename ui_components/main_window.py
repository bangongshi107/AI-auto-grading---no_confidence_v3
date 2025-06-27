import sys
import os
import time
import traceback
import pyautogui
from PyQt5.QtWidgets import (QMainWindow, QWidget, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox, QShortcut,
                             QComboBox, QRadioButton, QButtonGroup, QTextBrowser, QPlainTextEdit, QSpinBox, QProgressBar,
                             QApplication) # <--- 新增 QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5 import uic
from .question_config_dialog import MyWindow2, QuestionConfigDialog

class MainWindow(QMainWindow):
    """
    主窗口类，负责处理UI相关的逻辑和交互
    """
    # 定义信号
    update_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str, bool)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal()

    def __init__(self, config_manager, api_service, worker):
        """
        初始化主窗口

        Args:
            config_manager: 配置管理器实例
            api_service: API服务实例
            worker: 自动线程实例
        """
        super().__init__()

        # 保存依赖项
        self.config_manager = config_manager
        self.api_service = api_service
        self.worker = worker

        # 添加初始化标志，避免重复操作
        self._is_initializing = True # 初始化开始

        # 加载UI文件
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe，使用PyInstaller的临时路径
            base_path = sys._MEIPASS
        else:
            # 否则，使用当前文件所在的目录
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        ui_path = os.path.join(base_path, "setting", "多题.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
        else:
            print(f"UI文件不存在：{ui_path}")
            sys.exit(1)

        # 初始化组件
        # self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint) # 临时注释掉测试
        # 用字典存储每道题的答案框窗口
        self.answer_windows = {}  # {question_index: MyWindow2实例}

        # 初始化多题目支持
        self.current_question = 1  # 当前选中的题目
        self.max_questions = 4     # 最多支持的题目数量

        # 设置ESC快捷键
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.stop_auto_thread)

        # 初始化UI元素缓存
        self._ui_cache = {}

        # 初始化UI (包括加载配置到UI和连接信号)
        self.init_ui()

        # 连接工作线程信号
        self.connect_signals()

        # 注意: API服务的配置更新现在由 main.py 中的 Application.load_config 协调
        # MainWindow 不再直接设置 ApiService 的 API 密钥，而是通过 ConfigManager 间接同步

        # 显示窗口
        self.show()

        # 初始化完成后设置标志
        self._is_initializing = False # 初始化完成

        # 日志初始化完成信息
        self.log_message("主窗口初始化完成")

    def _update_config_from_ui_and_save(self):
        """
        此方法已被重构，所有配置项现在使用即时保存逻辑。
        该方法保留仅用于兼容性，但不再执行任何操作。
        """
        pass

    def handle_lineEdit_save(self, field_name, value):
        """处理 QLineEdit 的内存更新"""
        if self._is_initializing: return
        if self.config_manager:
            self.config_manager.update_config_in_memory(field_name, value)
            self.log_message(f"配置项 '{field_name}' 已在内存中更新为: {value}")

    def handle_plainTextEdit_save(self, field_name, value):
        """处理 QPlainTextEdit 的内存更新 (例如标准答案)"""
        if self._is_initializing: return
        if self.config_manager:
            self.config_manager.update_config_in_memory(field_name, value)
            self.log_message(f"配置项 '{field_name}' 已在内存中更新") # plainTextEdit 的日志可以更简洁

    def handle_spinBox_save(self, field_name, value):
        """处理 QSpinBox 的内存更新"""
        if self._is_initializing: return
        if self.config_manager:
            self.config_manager.update_config_in_memory(field_name, value)
            self.log_message(f"配置项 '{field_name}' 已在内存中更新为: {value}")

    def handle_comboBox_save(self, field_name, value):
        """处理 QComboBox 的内存更新"""
        if self._is_initializing: return
        if self.config_manager:
            self.config_manager.update_config_in_memory(field_name, value)
            self.log_message(f"配置项 '{field_name}' 已在内存中更新为: {value}")

    def handle_checkBox_save(self, field_name, state):
        """处理 QCheckBox 的内存更新"""
        if self._is_initializing: return
        value = bool(state)
        if self.config_manager:
            self.config_manager.update_config_in_memory(field_name, value)
            self.log_message(f"配置项 '{field_name}' 已在内存中更新为: {value}")

    def _show_save_error_and_disable_ui(self, error_message):
        """当保存配置失败时，显示错误弹窗并禁用所有UI操作。"""
        QMessageBox.critical(self, "保存配置失败",
                             f"保存配置时发生严重错误:\n{error_message}\n\n"
                             "应用程序所有操作已被禁用。\n"
                             "请检查配置文件权限、路径或磁盘空间，并尝试解决问题。\n"
                             "解决后，您需要重启应用程序。")
        self._set_all_controls_enabled(False) # 禁用所有控件

    def _set_all_controls_enabled(self, enabled):
        """启用或禁用所有关键UI控件。"""
        # 需要禁用/启用的控件列表
        controls_names = [
            'auto_run_but', 'stop_but', 'api_test_button',
            'first_api_key', 'first_modelID', 'first_api_url',
            'second_api_key', 'second_modelID', 'second_api_url',
            'dual_evaluation_enabled', 'score_diff_threshold',
            'subject_text', 'cycle_number', 'wait_time',
            'log_text', 'work'
        ]
        for i in range(1, self.max_questions + 1):
            controls_names.append(f'configQuestion{i}')
            controls_names.append(f'StandardAnswer_text_{i}')
            if i > 1:
                controls_names.append(f'enableQuestion{i}')

        for name in controls_names:
            widget = self.get_ui_element(name)
            if widget:
                widget.setEnabled(enabled)

        if not enabled:
            self.log_message("由于保存错误，所有操作已禁用。请解决问题后重启。", is_error=True)
        # 注意: 如果未来需要“重试保存”功能，重新启用控件时需要小心恢复其之前的逻辑状态。
        # 当前需求是禁用并提示重启。

    def _connect_direct_edit_save_signals(self):
        """连接直接编辑字段的信号以触发即时保存机制。"""
        # API 输入字段 - 从 textChanged 改为 editingFinished
        api_fields = ['first_api_key', 'first_modelID', 'first_api_url',
                      'second_api_key', 'second_modelID', 'second_api_url']
        for field_name in api_fields:
            widget = self.get_ui_element(field_name, QLineEdit)
            if widget:
                widget.editingFinished.connect(
                    lambda field=field_name, w=widget: self.handle_lineEdit_save(field, w.text())
                )

        # 循环次数和等待时间 - QSpinBox
        cycle_widget = self.get_ui_element('cycle_number', QSpinBox)
        if cycle_widget:
            cycle_widget.valueChanged.connect(
                lambda value, field="cycle_number": self.handle_spinBox_save(field, value)
            )

        wait_widget = self.get_ui_element('wait_time', QSpinBox)
        if wait_widget:
            wait_widget.valueChanged.connect(
                lambda value, field="wait_time": self.handle_spinBox_save(field, value)
            )

        # 标准答案文本框 - 从 textChanged 改为失去焦点触发
        for i in range(1, self.max_questions + 1):
            # 假设 StandardAnswer_text_i 是 QPlainTextEdit
            std_answer_widget = self.get_ui_element(f'StandardAnswer_text_{i}', QPlainTextEdit)
            if std_answer_widget:
                self._connect_plain_text_edit_save_signal(std_answer_widget, i)

        self.log_message("直接编辑字段的即时保存信号已连接")

    def _connect_plain_text_edit_save_signal(self, widget, question_index):
        """为 QPlainTextEdit 连接失去焦点时的保存信号 - 使用事件过滤器方式"""
        # 标记这个widget需要在失去焦点时保存
        widget.setProperty('question_index', question_index)
        widget.setProperty('needs_save_on_focus_out', True)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器，处理文本框失去焦点事件"""
        if (event.type() == event.FocusOut and
            hasattr(obj, 'property') and
            obj.property('needs_save_on_focus_out')):

            question_index = obj.property('question_index')
            text_widget = obj
            field_name = f"question_{question_index}_standard_answer"
            self.handle_plainTextEdit_save(field_name, text_widget.toPlainText())
            self.log_message(f"第{question_index}题标准答案编辑完成")

        return super().eventFilter(obj, event)

    def log_message(self, message, is_error=False):
        """
        记录日志消息

        Args:
            message: 日志消息
            is_error: 是否为错误消息
        """
        try:
            log_text = self.get_ui_element('log_text')
            if log_text:
                if is_error:
                    log_text.append(f'<span style="color:red">[错误] {message}</span>')
                else:
                    log_text.append(f'<span style="color:blue">[信息] {message}</span>')
                log_text.verticalScrollBar().setValue(log_text.verticalScrollBar().maximum())
            print(f"[{'错误' if is_error else '信息'}] {message}")
        except AttributeError as e:
            print(f"记录日志失败（AttributeError）：{str(e)}")
            print(f"原始消息：[{'错误' if is_error else '信息'}] {message}")
        except ValueError as e: # Added ValueError for completeness
            print(f"记录日志失败（ValueError）：{str(e)}")
            print(f"原始消息：[{'错误' if is_error else '信息'}] {message}")
        except Exception as e:
            print(f"记录日志失败（未知错误）：{str(e)}")
            print(f"原始消息：[{'错误' if is_error else '信息'}] {message}")

    def init_ui(self):
        """初始化UI组件"""
        try:
            self.setup_question_selector()
            self.connect_buttons() # 连接操作按钮的 clicked 信号
            self.setup_text_fields() # 设置文本框占位符等

            # 这些 setup 方法内部连接的 on_X_changed 处理器将调用 _update_config_from_ui_and_save
            self.setup_comboboxes()    # subject_text.currentIndexChanged -> on_subject_changed
            self.setup_dual_evaluation() # dual_evaluation_enabled.stateChanged -> on_dual_evaluation_changed
                                         # score_diff_threshold.valueChanged -> on_score_diff_threshold_changed

            # 连接题目启用复选框的 stateChanged 信号
            for i in range(2, self.max_questions + 1):
                checkbox_name = f'enableQuestion{i}'
                checkbox = self.get_ui_element(checkbox_name, QCheckBox) # getattr(self, checkbox_name, None)
                if checkbox:
                    checkbox.stateChanged.connect(self.on_question_enabled_changed)

            self.setup_config_buttons() # 设置配置按钮的初始状态

            self.load_config_to_ui() # 将配置加载到UI控件

            # 连接那些用户可以直接编辑并应立即触发保存的字段的信号
            self._connect_direct_edit_save_signals()

            self.log_message("UI组件初始化完成")
        except AttributeError as e:
            self.log_message(f"初始化UI组件出错（AttributeError）: {str(e)}", is_error=True)
        except ValueError as e:
            self.log_message(f"初始化UI组件出错（ValueError）: {str(e)}", is_error=True)
        except Exception as e:
            self.log_message(f"初始化UI组件出错（未知错误）: {str(e)}", is_error=True)

    def setup_question_selector(self):
        """设置题目选择器"""
        try:
            self.question_button_group = QButtonGroup(self)
            self.question_button_group.buttonClicked.connect(self.on_question_changed)
        except Exception as e:
            self.log_message(f"添加题目选择器出错: {str(e)}", is_error=True)

    def setup_config_buttons(self):
        """设置配置按钮初始状态"""
        try:
            config_button1 = self.get_ui_element('configQuestion1')
            if config_button1:
                config_button1.setEnabled(True)

            for i in range(2, self.max_questions + 1):
                config_button = self.get_ui_element(f'configQuestion{i}')
                if config_button:
                    config_button.setEnabled(False)
                checkbox = self.get_ui_element(f'enableQuestion{i}')
                if checkbox and i > 2: # Q2 enable checkbox depends on Q1 (always enabled)
                    checkbox.setEnabled(False)
        except AttributeError as e:
            self.log_message(f"设置配置按钮出错（AttributeError）: {str(e)}", is_error=True)
        except ValueError as e:
            self.log_message(f"设置配置按钮出错（ValueError）: {str(e)}", is_error=True)
        except Exception as e:
            self.log_message(f"设置配置按钮出错: {str(e)}", is_error=True)

    def connect_buttons(self):
        """连接按钮点击事件"""
        try:
            auto_run_but = self.get_ui_element('auto_run_but')
            if auto_run_but:
                auto_run_but.clicked.connect(self.auto_run_but_clicked)

            stop_but = self.get_ui_element('stop_but')
            if stop_but:
                stop_but.clicked.connect(self.stop_auto_thread)

            api_test_button = self.get_ui_element('api_test_button')
            if api_test_button:
                api_test_button.clicked.connect(self.test_api_connections)

            for i in range(1, self.max_questions + 1):
                button_name = f'configQuestion{i}'
                config_button = self.get_ui_element(button_name)
                if config_button:
                    config_button.clicked.connect(lambda checked, q=i: self.open_question_config_dialog(q))
                else:
                    self.log_message(f"未找到题目配置按钮 '{button_name}'", is_error=True)

        except Exception as e:
            self.log_message(f"连接按钮事件出错: {str(e)}", is_error=True)

    def setup_comboboxes(self):
        """设置下拉菜单"""
        try:
            subject_combobox = self.get_ui_element('subject_text')
            if subject_combobox:
                subject_combobox.currentIndexChanged.connect(self.on_subject_changed)
                # 加载当前配置中的科目在 load_config_to_ui 中处理
        except Exception as e:
            self.log_message(f"设置下拉菜单出错: {str(e)}", is_error=True)

    def setup_text_fields(self):
        """设置文本框"""
        try:
            for i in range(1, self.max_questions + 1):
                standard_answer = self.get_ui_element(f'StandardAnswer_text_{i}')
                if standard_answer:
                    standard_answer.setPlaceholderText(f"请输入第{i}题的评分细则...")
        except Exception as e:
            self.log_message(f"设置文本框出错: {str(e)}", is_error=True)

    def connect_signals(self):
        """连接信号，防止重复连接"""
        if hasattr(self, '_signals_connected') and self._signals_connected:
            return
        try:
            if hasattr(self.worker, 'update_signal'): self.worker.update_signal.disconnect()
            if hasattr(self.worker, 'log_signal'): self.worker.log_signal.disconnect()
            if hasattr(self.worker, 'progress_signal'): self.worker.progress_signal.disconnect()
            if hasattr(self.worker, 'finished_signal'): self.worker.finished_signal.disconnect()
            if hasattr(self.worker, 'error_signal'): self.worker.error_signal.disconnect()
        except: pass

        try:
            # self.worker.update_signal.connect(self.update_suggestion_text) # 暂时禁用，因为UI上没有对应组件
            self.worker.log_signal.connect(self.log_message)
            # self.worker.progress_signal.connect(self.update_progress) # 暂时禁用，因为UI在运行时最小化
            self.worker.finished_signal.connect(self.on_worker_finished)
            if hasattr(self.worker, 'error_signal'):
                self.worker.error_signal.connect(lambda msg: self.log_message(msg, True))
            self._signals_connected = True
            self.log_message("工作线程信号已连接")
        except AttributeError as e:
            self.log_message(f"连接信号出错（AttributeError）: {str(e)}", is_error=True)
        except Exception as e:
            self.log_message(f"连接信号出错: {str(e)}", is_error=True)

    def get_or_create_answer_window(self, question_index):
        """获取或创建指定题目的答案框窗口"""
        if question_index not in self.answer_windows:
            window = MyWindow2(parent=None, question_index=question_index) # <--- 核心修改点
            window.main_window = self
            window.status_changed.connect(lambda status, q_idx=question_index: self.on_window_status_changed(status, q_idx))
            self.answer_windows[question_index] = window
        return self.answer_windows[question_index]

    def on_window_status_changed(self, status, question_index):
        """处理答案框窗口状态变化"""
        try:
            self.log_message(f"第{question_index}题答案框状态变化: {status}")
            # ... (original logic)
        except Exception as e:
            self.log_message(f"处理第{question_index}题答案框状态变化出错: {str(e)}", is_error=True)

    def setup_api_service(self):
        """
        此方法不再直接设置ApiService的API密钥或更新ConfigManager。
        ApiService的配置更新现在由Application.load_config协调，
        它会调用ApiService.update_config_from_manager()。
        MainWindow只负责从UI读取值并更新ConfigManager的内存，
        然后由ConfigManager的保存机制将这些值写入文件。
        """
        try:
            # 即时保存逻辑已处理所有配置更新，此处无需额外操作
            # 仅在非初始化阶段记录消息，避免启动时重复日志
            if not self._is_initializing:
                self.log_message("API服务配置已在UI中更新，等待自动保存。")
        except Exception as e:
            self.log_message(f"设置API服务出错: {str(e)}", is_error=True)

    def on_question_changed(self, button):
        """处理题目选择变更事件"""
        try:
            question_index = self.question_button_group.id(button)
            if question_index < 1 or question_index > self.max_questions:
                self.log_message(f"无效的题目索引: {question_index}", is_error=True)
                return
            self.current_question = question_index
            # 移除对 config_manager.apply_question_config 的调用
            # 题目配置的加载和显示应由 load_config_to_ui 或直接从 config_manager 读取完成
            self.load_config_to_ui() # 重新加载所有配置到UI，确保当前题目配置正确显示
            self.log_message(f"已切换到第{question_index}题配置")
        except Exception as e:
            self.log_message(f"切换题目配置出错: {str(e)}", is_error=True)

    def on_subject_changed(self, index):
        """处理科目选择变更事件"""
        try:
            # 此方法由 subject_combobox.currentIndexChanged 信号连接
            # UI逻辑（如日志）在此处处理
            subject_combobox = self.get_ui_element('subject_text')
            if subject_combobox:
                self.log_message(f"科目已在内存中更新为: {subject_combobox.currentText()}")
                self.handle_comboBox_save('subject', subject_combobox.currentText())
        except Exception as e:
            self.log_message(f"更新科目设置时出错: {str(e)}", is_error=True)

    def update_ui_state(self, is_running):
        """根据自动阅卷的运行状态更新UI控件的启用/禁用状态，并管理窗口最小化/恢复。"""

        print(f"DEBUG: update_ui_state called with is_running={is_running}")

        start_button = self.get_ui_element('auto_run_but')
        stop_button = self.get_ui_element('stop_but')

        # ... (启用/禁用其他控件的逻辑不变) ...
        if start_button:
            start_button.setEnabled(not is_running)
        if stop_button:
            stop_button.setEnabled(is_running)

        config_related_control_names = [
            'api_test_button', 'first_api_key', 'first_modelID', 'first_api_url',
            'second_api_key', 'second_modelID', 'second_api_url',
            'dual_evaluation_enabled', 'score_diff_threshold', 'subject_text',
            'cycle_number', 'wait_time',
        ]
        for i in range(1, self.max_questions + 1):
            config_related_control_names.append(f'configQuestion{i}')
            config_related_control_names.append(f'StandardAnswer_text_{i}')
            if self.get_ui_element(f'enableQuestion{i}'):
                 config_related_control_names.append(f'enableQuestion{i}')

        for name in config_related_control_names:
            widget = self.get_ui_element(name)
            if widget:
                widget.setEnabled(not is_running)
        # --- 结束控件启用/禁用逻辑 ---


        # --- 窗口状态管理逻辑 ---
        if is_running:
            self.log_message("自动阅卷进行中，配置项已禁用，窗口将最小化。")
            if not self.isMinimized():
                self.showMinimized()
        else: # is_running is False (任务结束或停止时)
            # 检查是否有配置对话框正在等待关闭

            print("DEBUG: update_ui_state: is_running is False, attempting to show normal if needed.")
            if self.isMinimized():
                self.log_message("自动阅卷已停止/完成，正在恢复主窗口 (从最小化状态)...")
                self.showNormal()
                self.activateWindow()
            else: # 窗口已经是 normal 和 visible
                 self.log_message("自动阅卷已停止/完成，主窗口已是正常状态。")


            # 确保双评相关的UI状态也根据当前配置正确刷新 (如果任务结束时需要)
            if hasattr(self, 'check_dual_evaluation_availability'):
                self.check_dual_evaluation_availability()
            # self.log_message("自动阅卷已停止/完成，配置项已启用，窗口已恢复。") # 这条日志可能需要根据上面的条件调整
        # --- 结束窗口状态管理逻辑 ---

    def auto_run_but_clicked(self):
        """自动运行按钮点击事件"""
        try:
            # --- 首先，保存所有当前内存中的配置到文件 ---
            self.log_message("尝试在运行前保存所有配置...")
            save_success = self.config_manager.save_all_configs_to_file()
            if not save_success:
                self.log_message("错误：运行前保存配置失败！无法启动自动阅卷。", is_error=True)
                QMessageBox.critical(self, "保存配置失败",
                                     "在尝试启动自动阅卷前，保存当前配置失败。\n"
                                     "请检查日志或配置文件权限。自动阅卷未启动。")
                return # 阻止运行
            self.log_message("所有配置已成功保存。")
            # --- 结束保存逻辑 ---

            if not self.check_required_settings(): # 这里的检查现在基于已保存的配置
                self.log_message("必要设置未完成，无法启动自动阅卷", is_error=True)
                return

            enabled_questions = [1]
            for i in range(2, self.max_questions + 1):
                checkbox = self.get_ui_element(f'enableQuestion{i}')
                if checkbox and checkbox.isChecked():
                    enabled_questions.append(i)

            if not enabled_questions:
                self.log_message("请至少启用一道题目", is_error=True)
                return

            for q_index in enabled_questions:
                q_config = self.config_manager.get_question_config(q_index)
                if not q_config or 'answer_area' not in q_config or not q_config['answer_area']:
                    self.log_message(f"请先为第{q_index}题框定答案区域", is_error=True)
                    return

            cycle_number = self.get_ui_element('cycle_number').value()
            wait_time = self.get_ui_element('wait_time').value()

            # --- 新增：获取并准备第一题三步打分配置 ---
            q1_config_data = self.config_manager.get_question_config(1) # 获取第一题的完整配置
            q1_enable_three_step_scoring = q1_config_data.get('enable_three_step_scoring', False)
            q1_score_input_pos_step1 = q1_config_data.get('score_input_pos_step1', None)
            q1_score_input_pos_step2 = q1_config_data.get('score_input_pos_step2', None)
            q1_score_input_pos_step3 = q1_config_data.get('score_input_pos_step3', None)
            q1_max_score_val = q1_config_data.get('max_score', 100) # 获取第一题的max_score

            # 判断是否为仅运行第一题的模式 (enabled_questions 是之前已获取的启用题目列表)
            is_single_q1_run = len(enabled_questions) == 1 and enabled_questions[0] == 1

            # 如果不是单题模式，但第一题配置了三步打分，则记录一个提示并禁用它
            if not is_single_q1_run and q1_enable_three_step_scoring:
                self.log_message("检测到多题目运行或非第一题运行，第一题的三步分数输入模式已自动禁用。", is_error=False)
                q1_enable_three_step_scoring = False # 强制禁用
            # --- 结束新增部分 ---

            dual_evaluation = False
            score_diff_threshold = 5 # Default

            if is_single_q1_run: # 使用新的变量
                dual_eval_checkbox = self.get_ui_element('dual_evaluation_enabled')
                if dual_eval_checkbox and dual_eval_checkbox.isChecked():
                    dual_evaluation = True
                    score_diff_spinbox = self.get_ui_element('score_diff_threshold')
                    if score_diff_spinbox:
                        score_diff_threshold = score_diff_spinbox.value()
                    self.log_message(f"已启用双评模式，分差阈值: {score_diff_threshold}")

            question_configs = []
            for q_index in enabled_questions:
                q_config = self.config_manager.get_question_config(q_index)
                if not q_config:
                    self.log_message(f"第{q_index}题配置不存在", is_error=True)
                    continue
                q_config['question_index'] = q_index # 确保 question_index 在配置内
                # 双评仅对单题模式下的第一题生效
                q_config['dual_eval_enabled'] = dual_evaluation if q_index == 1 and is_single_q1_run else False

                # 为第一题添加三步打分和最大分配置 (如果启用)
                if q_index == 1:
                    q_config['enable_three_step_scoring'] = q1_enable_three_step_scoring
                    q_config['score_input_pos_step1'] = q1_score_input_pos_step1
                    q_config['score_input_pos_step2'] = q1_score_input_pos_step2
                    q_config['score_input_pos_step3'] = q1_score_input_pos_step3
                    q_config['max_score'] = q1_max_score_val # 确保第一题的max_score被正确传递

                # 确认 question_type 是否存在，并记录其值 (在添加到列表前)
                current_q_type = q_config.get('question_type')
                if not current_q_type:
                    # 这种情况理论上不应该发生，因为 ConfigManager 在加载时会提供默认值
                    default_fallback_q_type = 'Subjective_PointBased_QA'
                    self.log_message(
                        f"严重警告：第{q_index}题配置中未找到 'question_type'。"
                        f"将强制使用默认类型 '{default_fallback_q_type}'。请检查ConfigManager逻辑。",
                        is_error=True
                    )
                    q_config['question_type'] = default_fallback_q_type # 强制设置一个后备
                else:
                    # 记录将要用于当前题目的类型
                    self.log_message(f"第{q_index}题将使用的题目类型: {current_q_type}", False)

                question_configs.append(q_config) # 将处理好的 q_config 添加到列表

            # --- 在 question_configs 列表完全构建后，准备参数给 AutoThread ---
            # (之前错误的外部 for 循环日志块已被移除)

            # 准备参数给 AutoThread
            params_for_worker = {
                'cycle_number': cycle_number,
                'wait_time': wait_time,
                'question_configs': question_configs, # 这个列表现在包含了每个题目的正确配置
                'dual_evaluation': dual_evaluation, # 这是全局双评开关，具体到题目由q_config['dual_eval_enabled']控制
                'score_diff_threshold': score_diff_threshold,
                'first_model_id': self.config_manager.first_modelID,
                'second_model_id': self.config_manager.second_modelID,
                'is_single_question_one_run': is_single_q1_run
            }

            # 设置参数并启动线程
            self.worker.set_parameters(**params_for_worker)
            self.worker.start() # 调用 QThread 的标准 start() 方法

            self.update_ui_state(is_running=True)
            # if hasattr(self, 'start_timer'): self.start_timer() # 如果您有计时器逻辑
            self.log_message(f"自动阅卷已启动: 循环次数={cycle_number}, 等待时间={wait_time}秒")
        except AttributeError as e:
            self.log_message(f"启动自动阅卷出错（AttributeError）: {str(e)}", is_error=True)
            traceback.print_exc() # 打印更详细的AttributeError追踪信息
        except ValueError as e:
            self.log_message(f"启动自动阅卷出错（ValueError）: {str(e)}", is_error=True)
            traceback.print_exc()
        except Exception as e:
            self.log_message(f"启动自动阅卷出错: {str(e)}", is_error=True)
            traceback.print_exc()

    def check_required_settings(self):
        """检查必要的设置是否已配置"""
        try:
            enabled_questions = [1]
            for i in range(2, self.max_questions + 1):
                checkbox = self.get_ui_element(f'enableQuestion{i}')
                if checkbox and checkbox.isChecked():
                    enabled_questions.append(i)
            if not enabled_questions: return False

            # API Keys from ConfigManager (which should be in sync with UI)
            if not self.config_manager.first_api_key.strip(): return False # Simplified checks
            if not self.config_manager.first_modelID.strip(): return False
            if not self.config_manager.first_api_url.strip(): return False

            # Dual eval check from ConfigManager
            # dual_eval_settings = self.config_manager.get_dual_evaluation_settings()
            # if dual_eval_settings['enabled']:
            # Simplified: directly check config_manager attributes if they exist
            if getattr(self.config_manager, 'dual_evaluation_enabled', False):
                 if not self.config_manager.second_api_key.strip(): return False
                 if not self.config_manager.second_modelID.strip(): return False
                 if not self.config_manager.second_api_url.strip(): return False

            for question_index in enabled_questions:
                q_cfg = self.config_manager.get_question_config(question_index)
                if not q_cfg or not q_cfg.get('standard_answer', '').strip():
                    self.log_message(f"错误：第{question_index}题已启用但未设置标准答案", is_error=True)
                    return False
            return True
        except Exception as e:
            self.log_message(f"检查必要设置时出错: {str(e)}", is_error=True)
            return False

    def stop_auto_thread(self):
        """停止自动线程。"""
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop() # 请求停止
                self.log_message("已发送停止请求至自动阅卷线程。")
            else:
                self.log_message("自动阅卷未在运行或已停止。")
                # 确保UI在非运行状态
                self.update_ui_state(is_running=False)
        except Exception as e:
            self.log_message(f"停止自动线程时出错: {str(e)}", is_error=True)


    def start_area_selection(self):
        """开始选择答案区域"""
        try:
            self.log_message("请通过题目配置对话框来框定答案区域")
            self.open_question_config_dialog() # Uses current_question
        except Exception as e:
            self.log_message(f"启动答案区域选择出错: {str(e)}", is_error=True)

    def on_question_enabled_changed(self, state):
        """处理题目启用状态变更，触发内存更新和UI约束应用。"""
        if self._is_initializing: return

        sender_checkbox = self.sender()
        if not sender_checkbox: return

        try:
            question_index_str = sender_checkbox.objectName().replace('enableQuestion', '')
            question_index = int(question_index_str)
            is_enabled = bool(state)

            # 1. 更新内存中的配置
            self.handle_checkBox_save(f"question_{question_index}_enabled", is_enabled)

            # 2. 应用所有UI约束
            self._apply_ui_constraints()

            self.log_message(f"第{question_index}题状态已更新，UI约束已重新应用。")
        except (ValueError, AttributeError) as e:
            self.log_message(f"处理题目启用状态变更时出错: {str(e)}", is_error=True)
    def update_config_button(self, question_index, is_enabled):
        """更新配置按钮状态"""
        config_button = self.get_ui_element(f'configQuestion{question_index}')
        if config_button:
            config_button.setEnabled(is_enabled)

    def _apply_ui_constraints(self):
        """
        集中处理所有UI控件间的约束逻辑。
        此方法是UI状态的唯一真理来源。
        """
        # 1. 获取当前状态
        enabled_questions_indices = [1]
        for i in range(2, self.max_questions + 1):
            cb = self.get_ui_element(f'enableQuestion{i}')
            if cb and cb.isChecked():
                enabled_questions_indices.append(i)

        is_single_q1_mode = len(enabled_questions_indices) == 1

        q1_config = self.config_manager.get_question_config(1)
        is_q1_three_step_enabled = q1_config.get('enable_three_step_scoring', False)

        # 2. 应用双评约束 (仅单题模式可用)
        dual_eval_checkbox = self.get_ui_element('dual_evaluation_enabled')
        if dual_eval_checkbox:
            dual_eval_checkbox.setEnabled(is_single_q1_mode)
            if not is_single_q1_mode and dual_eval_checkbox.isChecked():
                dual_eval_checkbox.blockSignals(True)
                dual_eval_checkbox.setChecked(False)
                # 直接更新内存和UI，因为这是逻辑强制的
                self.handle_checkBox_save('dual_evaluation_enabled', False)
                self.log_message("多题模式已激活，双评功能已自动禁用。", is_error=False)
                dual_eval_checkbox.blockSignals(False)

            # 更新第二API相关字段的可用状态
            is_dual_active = dual_eval_checkbox.isChecked() and dual_eval_checkbox.isEnabled()
            self.get_ui_element('score_diff_threshold').setEnabled(is_dual_active)
            for field in ['second_api_key', 'second_modelID', 'second_api_url']:
                self.get_ui_element(field).setEnabled(is_dual_active)

        # 3. 应用三步打分与题目级联约束
        # 如果三步打分启用，则必然是单题模式，需要禁用其他题目
        # 如果多题模式启用，则需要确保三步打分被禁用 (在配置对话框中处理，此处主要处理级联)

        can_enable_next_question = True  # Q1总是可用
        for i in range(2, self.max_questions + 1):
            checkbox_i = self.get_ui_element(f'enableQuestion{i}')
            if not checkbox_i: continue

            # 一个题目可选的前提是：前一个题目被勾选了，且Q1的三步打分未启用
            should_be_enabled = can_enable_next_question and not is_q1_three_step_enabled
            checkbox_i.setEnabled(should_be_enabled)

            if not should_be_enabled and checkbox_i.isChecked():
                checkbox_i.blockSignals(True)
                checkbox_i.setChecked(False)
                self.handle_checkBox_save(f'question_{i}_enabled', False)
                self.log_message(f"因前置条件不满足，第{i}题被自动禁用。", is_error=False)
                checkbox_i.blockSignals(False)

            # 更新当前题目的配置按钮状态
            self.update_config_button(i, checkbox_i.isChecked())

            # 为下一轮循环设置前提条件
            can_enable_next_question = checkbox_i.isChecked()
    def setup_dual_evaluation(self):
        """设置双评相关UI组件。"""
        try:
            dual_eval_checkbox = self.get_ui_element('dual_evaluation_enabled')
            if dual_eval_checkbox:
                self.dual_evaluation_checkbox = dual_eval_checkbox
                self.dual_evaluation_checkbox.stateChanged.connect(self.on_dual_evaluation_changed)

            score_diff_spinbox = self.get_ui_element('score_diff_threshold')
            if score_diff_spinbox:
                self.score_diff_threshold_spinbox = score_diff_spinbox
                self.score_diff_threshold_spinbox.valueChanged.connect(self.on_score_diff_threshold_changed)
                self.score_diff_threshold_spinbox.setMinimum(1)
                self.score_diff_threshold_spinbox.setMaximum(50)

            # 注意：加载和应用约束的逻辑已移至 load_config_to_ui
        except Exception as e:
            self.log_message(f"初始化双评设置出错: {str(e)}", is_error=True)

    def load_dual_evaluation_settings(self):
        """从配置管理器加载双评设置到UI"""
        try:
            # 假设ConfigManager有get_dual_evaluation_settings方法或直接属性
            # settings = self.config_manager.get_dual_evaluation_settings()
            # For example, if ConfigManager has direct attributes:
            enabled = getattr(self.config_manager, 'dual_evaluation_enabled', False)
            threshold = getattr(self.config_manager, 'score_diff_threshold', 5)

            dual_eval_checkbox = self.get_ui_element('dual_evaluation_enabled')
            if dual_eval_checkbox:
                dual_eval_checkbox.setChecked(enabled)

            score_diff_threshold_spinbox = self.get_ui_element('score_diff_threshold')
            if score_diff_threshold_spinbox:
                score_diff_threshold_spinbox.setValue(threshold)
                score_diff_threshold_spinbox.setEnabled(enabled) # <--- 添加此行

            self.log_message("双评设置已从配置加载到UI")
        except Exception as e:
            self.log_message(f"加载双评设置到UI出错: {str(e)}", is_error=True)

    # save_dual_evaluation_settings(self) method removed.

    def on_score_diff_threshold_changed(self, value):
        """处理分差阈值变化，并触发配置保存"""
        try:
            # 此方法由 score_diff_threshold.valueChanged 信号连接
            self.log_message(f"分差阈值已在内存中更新为: {value}")
            self.handle_spinBox_save('score_diff_threshold', value)
        except Exception as e:
            self.log_message(f"更新分差阈值时出错: {str(e)}", is_error=True)

    def test_api_connections(self):
        """测试API连接"""
        try:
            self.setup_api_service() # Ensures api_service has latest keys from UI/ConfigManager

            self.log_message("正在测试第一组API连接...")
            success1, message1 = self.api_service.test_api_connection("first")

            # dual_eval_enabled = self.config_manager.dual_evaluation_enabled # From ConfigManager
            dual_eval_checkbox = self.get_ui_element('dual_evaluation_enabled')
            dual_eval_enabled_ui = dual_eval_checkbox.isChecked() and dual_eval_checkbox.isEnabled() if dual_eval_checkbox else False


            result_message = ""
            if dual_eval_enabled_ui:
                self.log_message("已开启双评模式，正在测试第二组API连接...")
                success2, message2 = self.api_service.test_api_connection("second")
                result_message = (
                    f"API测试结果:\n\n第一组API: {'✓ ' if success1 else '✗ '}{message1}\n\n"
                    f"第二组API: {'✓ ' if success2 else '✗ '}{message2}\n\n"
                    f"已开启双评模式，{'两个API均测试成功' if success1 and success2 else '存在API测试失败'}"
                )
                if success1 and success2: self.log_message("API测试完成：两个API均可正常使用")
                else: self.log_message("API测试完成：存在API无法正常使用", is_error=True)
            else:
                result_message = f"API测试结果:\n\n第一组API: {'✓ ' if success1 else '✗ '}{message1}"
                if success1: self.log_message("API测试完成：第一组API可正常使用")
                else: self.log_message("API测试完成：第一组API无法正常使用", is_error=True)

            QMessageBox.information(self, "API测试结果", result_message)
        except Exception as e:
            self.log_message(f"API测试出错: {str(e)}", is_error=True)
            QMessageBox.critical(self, "API测试错误", f"测试过程中发生错误:\n{str(e)}")

    def on_dual_evaluation_changed(self, state):
        """处理双评启用状态变化，并触发配置更新与UI约束应用。"""
        if self._is_initializing: return

        try:
            is_enabled = bool(state)
            # 1. 更新内存中的配置
            self.handle_checkBox_save('dual_evaluation_enabled', is_enabled)
            self.log_message(f"双评模式已在内存中更新为: {'启用' if is_enabled else '禁用'}。")

            # 2. 应用所有UI约束
            self._apply_ui_constraints()

        except Exception as e:
            self.log_message(f"更新双评设置时出错: {str(e)}", is_error=True)

    def get_ui_element(self, element_name, element_type=None):
        """统一且高效的UI元素获取方法"""
        try:
            if element_name in self._ui_cache:
                element = self._ui_cache[element_name]
                if element and (not hasattr(element, 'parent') or element.parent()): # Check validity
                    return element
                else:
                    del self._ui_cache[element_name] # Stale cache

            element = None
            if hasattr(self, element_name): # Direct attribute
                element = getattr(self, element_name)
                if self._is_valid_ui_element(element, element_type):
                    self._ui_cache[element_name] = element
                    return element

            if element_type: # Specific type find
                element = self.findChild(element_type, element_name)
                if element:
                    self._ui_cache[element_name] = element
                    return element

            # Common types (order might matter for performance if names overlap)
            common_types = [QLineEdit, QComboBox, QCheckBox, QPushButton, QLabel,
                            QPlainTextEdit, QTextBrowser, QSpinBox, QProgressBar, QRadioButton]
            for widget_type in common_types:
                element = self.findChild(widget_type, element_name)
                if element:
                    self._ui_cache[element_name] = element
                    return element

            element = self.findChild(QWidget, element_name) # Generic fallback
            if element:
                self._ui_cache[element_name] = element
                return element

            return None
        except Exception as e:
            # 当 get_ui_element 自身发生错误时，特别是查找 'log_text' 失败，
            # 不能再调用 self.log_message，否则会无限递归。
            # 直接打印到控制台。
            print(f"[CRITICAL_ERROR in get_ui_element] 获取UI元素 '{element_name}' 出错: {str(e)}")
            print(f"[CRITICAL_ERROR in get_ui_element] Traceback: {traceback.format_exc()}")
            return None

    def _is_valid_ui_element(self, element, expected_type=None):
        """检查获取的UI元素是否有效且符合预期类型"""
        if element is None:
            return False
        # 简单检查它是否是一个 QObject (所有QWidget都是QObject)
        from PyQt5.QtCore import QObject
        if not isinstance(element, QObject):
            return False
        if expected_type and not isinstance(element, expected_type):
            # 可以选择性地记录一个警告，但对于此方法的目的，主要关注元素是否存在
            # print(f"UI Element type mismatch for {getattr(element, 'objectName', lambda: 'Unknown')()}: expected {expected_type}, got {type(element)}")
            return False # 如果类型不匹配则视为无效
        return True

    def load_config_to_ui(self):
        """将配置从ConfigManager加载到UI控件，并应用UI约束。"""
        if self._is_initializing and hasattr(self, '_config_loaded_once') and self._config_loaded_once:
            return

        self.log_message("正在加载配置到UI...")
        self._is_initializing = True  # 开始加载，阻止信号触发

        try:
            # API & 通用配置
            # ... (这部分代码保持不变，此处为缩写) ...
            api_fields_map = {
                'first_api_key': self.config_manager.first_api_key,
                'first_modelID': self.config_manager.first_modelID,
                'first_api_url': self.config_manager.first_api_url,
                'second_api_key': self.config_manager.second_api_key,
                'second_modelID': self.config_manager.second_modelID,
                'second_api_url': self.config_manager.second_api_url,
            }
            for field_name, value in api_fields_map.items():
                widget = self.get_ui_element(field_name, QLineEdit)
                if widget: widget.setText(str(value) if value is not None else "")

            subject_widget = self.get_ui_element('subject_text', QComboBox)
            if subject_widget:
                index = subject_widget.findText(self.config_manager.subject, Qt.MatchFixedString)
                if index >= 0: subject_widget.setCurrentIndex(index)

            self.get_ui_element('cycle_number').setValue(self.config_manager.cycle_number)
            self.get_ui_element('wait_time').setValue(self.config_manager.wait_time)

            # 双评设置
            dual_eval_cb = self.get_ui_element('dual_evaluation_enabled')
            if dual_eval_cb: dual_eval_cb.setChecked(self.config_manager.dual_evaluation_enabled)
            self.get_ui_element('score_diff_threshold').setValue(self.config_manager.score_diff_threshold)

            # 题目配置
            for i in range(1, self.max_questions + 1):
                q_config = self.config_manager.get_question_config(i)

                # Q1没有启用复选框，跳过
                if i > 1:
                    enable_checkbox = self.get_ui_element(f'enableQuestion{i}', QCheckBox)
                    if enable_checkbox:
                        enable_checkbox.setChecked(q_config.get('enabled', False))

                std_answer_widget = self.get_ui_element(f'StandardAnswer_text_{i}', QPlainTextEdit)
                if std_answer_widget:
                    std_answer_widget.setPlainText(q_config.get('standard_answer', ''))

            # 加载完成后，调用中央方法来应用所有UI约束
            self._apply_ui_constraints()

            self.log_message("配置已成功加载到UI并应用约束。")
            self._config_loaded_once = True

        except Exception as e:
            self.log_message(f"加载配置到UI时出错: {str(e)}\n{traceback.format_exc()}", is_error=True)
        finally:
            self._is_initializing = False # 加载完成，允许信号触发

    def update_progress(self, current_step, total_steps):
        """更新进度标签显示"""
        # # 该功能暂时禁用，因为UI在运行时最小化，用户不可见。
        # progress_label = self.get_ui_element('progress_status_label', QLabel)
        # if progress_label:
        #     if total_steps > 0:
        #         progress_label.setText(f"自动改卷进度: {current_step}/{total_steps}")
        #     else:
        #         progress_label.setText("等待开始...")
        pass

    def update_suggestion_text(self, text):
        """更新建议文本显示区域"""
        # 假设你的UI中有一个名为 'work' 的 QTextBrowser
        suggestion_widget = self.get_ui_element('work', QTextBrowser)
        if suggestion_widget:
            suggestion_widget.setHtml(text)
            suggestion_widget.verticalScrollBar().setValue(suggestion_widget.verticalScrollBar().maximum())
        else:
            # 如果 'work' 控件找不到，直接打印到控制台
            print(f"INFO: Suggestion update (work widget not found): {text[:200]}...")

    def on_worker_finished(self):
        """处理工作线程正常完成信号"""
        # self.log_message("所有阅卷任务已完成。") # update_ui_state 中会记录

        if hasattr(self, 'update_ui_state'):
            self.update_ui_state(is_running=False)
        else:
            print("[CRITICAL_ERROR] MainWindow is missing 'update_ui_state' method for on_worker_finished.")
            # 后备UI更新
            start_button = self.get_ui_element('auto_run_but')
            if start_button: start_button.setEnabled(True)
            stop_button = self.get_ui_element('stop_but')
            if stop_button: stop_button.setEnabled(False)

        # progress_label = self.get_ui_element('progress_status_label', QLabel)
        # if progress_label:
        #     progress_label.setText("任务已结束")

    def on_worker_error(self, error_message):
        """处理工作线程错误或特定中断信号"""
        self.log_message(f"任务中断: {error_message}", is_error=True)

        if hasattr(self, 'update_ui_state'):
            self.update_ui_state(is_running=False)
        else:
            print("[CRITICAL_ERROR] MainWindow is missing 'update_ui_state' method for on_worker_error.")
            # 后备UI更新和窗口恢复
            start_button = self.get_ui_element('auto_run_but')
            if start_button: start_button.setEnabled(True)
            stop_button = self.get_ui_element('stop_but')
            if stop_button: stop_button.setEnabled(False)
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()

        # progress_label = self.get_ui_element('progress_status_label', QLabel)
        # if progress_label:
        #     progress_label.setText("任务中断") # 或更具体的错误提示，但 Application 层会弹窗

    def open_question_config_dialog(self, question_index):
        """打开题目配置对话框"""

        print(f"DEBUG: Entering open_question_config_dialog for Q{question_index}")

        # 先定义一个内部函数来处理对话框的创建、显示和后续操作
        def _show_dialog_and_handle_result():
            print("DEBUG: _show_dialog_and_handle_result called")
            try:
                self.log_message(f"正在为第 {question_index} 题打开配置对话框...")

                # --- 计算 is_single_q1_mode_active ---
                is_single_q1_mode = True # 默认为 True
                if question_index == 1: # 仅当配置第一题时才需要判断
                    for i in range(2, self.max_questions + 1):
                        enable_checkbox = self.get_ui_element(f'enableQuestion{i}', QCheckBox)
                        if enable_checkbox and enable_checkbox.isChecked():
                            is_single_q1_mode = False
                            break
                else: # 如果不是配置第一题，这个标志无意义，但为了安全可以设为 False
                    is_single_q1_mode = False
                # --- 结束计算 ---

                dialog = QuestionConfigDialog(parent=self,
                                              config_manager=self.config_manager,
                                              question_index=question_index,
                                              is_single_q1_mode_active=is_single_q1_mode) # <--- 传递新参数
                dialog.setWindowModality(Qt.WindowModal)

                print("DEBUG: Before dialog.open()")
                result_code = dialog.exec_() # 阻塞直到对话框关闭
                print("DEBUG: After dialog.open()")

                # --- 对话框关闭后的处理 ---
                print(f"DEBUG: Dialog closed, result_code: {result_code}")

                if result_code == QDialog.Accepted:
                    self.load_config_to_ui()
                else:
                    self.log_message(f"第 {question_index} 题配置未更改 (对话框关闭，结果: {result_code})。")

            except Exception as e_dialog:
                if self:
                    self.log_message(f"处理第 {question_index} 题配置时出错: {str(e_dialog)}\n{traceback.format_exc()}", is_error=True)
                    QMessageBox.critical(self, "配置错误", f"处理题目 {question_index} 配置时发生错误:\n{str(e_dialog)}")

            finally: # <--- 关键：确保标志位被重置，并恢复窗口
                print("DEBUG: _show_dialog_and_handle_result finally block")
                if self: # 检查 self 是否仍然有效

                    self.log_message("主窗口状态已恢复。")


        _show_dialog_and_handle_result()

    def closeEvent(self, event):
        try:
            # 停止自动线程
            if hasattr(self.worker, 'running') and self.worker.running:
                self.worker.stop() # 请求停止，但不等待其完成，因为程序要关闭
                # self.worker.wait() # 如果需要确保线程完全停止再关闭，可以取消注释，但这可能使关闭变慢
                self.log_message("窗口关闭，请求停止自动运行线程...")

            # 关闭所有答案框窗口
            for window in list(self.answer_windows.values()):
                if window and window.isVisible():
                    window.close()
            self.answer_windows.clear()

            # --- 在关闭前保存所有配置 ---
            self.log_message("尝试在关闭程序前保存所有配置...")
            save_success = self.config_manager.save_all_configs_to_file()
            if not save_success:
                self.log_message("警告：关闭程序前保存配置失败。部分更改可能未保存。", is_error=True)
                # 可以选择是否给用户一个提示，但由于程序即将关闭，可能意义不大
                # QMessageBox.warning(self, "保存配置警告",
                #                      "在关闭程序时保存配置失败。\n"
                #                      "部分最近的配置更改可能未被保存。")
            else:
                self.log_message("所有配置已在关闭前成功保存。")
            # --- 结束保存逻辑 ---

            event.accept()
        except Exception as e:
            self.log_message(f"窗口关闭时出错: {str(e)}", is_error=True)
            # 即使出错，也尝试接受关闭事件，避免程序无法关闭
            event.accept() # 或者 event.ignore() 如果希望阻止关闭
