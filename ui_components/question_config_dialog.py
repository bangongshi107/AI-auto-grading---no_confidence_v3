from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QCheckBox, QGroupBox,
                            QComboBox, QTextEdit, QSpinBox, QMessageBox,
                            QMainWindow, QWidget)
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
import pyautogui
import time

class MyWindow2(QMainWindow):
    """答案框窗口类，用于框定答案区域"""
    
    # 添加信号，用于通知主窗口状态变化
    status_changed = pyqtSignal(str)
    
    def update_ui_state(self, is_running):
        """代理方法，转发到主窗口"""
        if hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'update_ui_state'):
            self.parent.update_ui_state(is_running)
        elif hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'update_ui_state'):
            self.main_window.update_ui_state(is_running)
    
    def __init__(self, parent=None, question_index=None):
        super(MyWindow2, self).__init__(parent)
        
        self.question_index = question_index
        
        # 根据题目编号设置不同的窗口标题
        title = f"第{question_index}题答案框" if question_index else "答案框"
        self.setWindowTitle(title)
        self.resize(400, 300)
        
        # 设置窗口样式 - 置顶、无边框、工具窗口
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        
        # 设置窗口属性为透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建中央窗口部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # 设置窗口背景为高透明度
        central_widget.setStyleSheet("background-color: rgba(200, 200, 255, 30);")
        
        # 初始化拖动和调整大小相关变量
        self.drag_position = QPoint()
        self.resizing = False
        self.resize_edge = None
        self.border_width = 8  # 边框宽度，用于检测鼠标是否在边缘
        
        # 添加锁定状态变量
        self.is_locked = False
        self.is_confirmed = False
        
        # 移除窗口提示，因为用户未看到且可能不需要
        pass
        
        print(f"第{question_index}题答案框窗口已创建" if question_index else "答案框窗口已创建")
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'log_message'): # 检查 main_window
            self.main_window.log_message(f"第{question_index}题答案框窗口已创建" if question_index else "答案框窗口已创建")
        elif hasattr(self.parent, 'log_message'): # 保留原始逻辑作为后备（尽管在此场景下parent为None）
            self.parent.log_message(f"第{question_index}题答案框窗口已创建" if question_index else "答案框窗口已创建")
    
    def set_confirmed_mode(self):
        """设置为已确认模式，更改提示文字和透明度"""
        self.is_confirmed = True
        # 增加透明度，使窗口更不明显但仍然可见
        self.centralWidget().setStyleSheet("background-color: rgba(200, 200, 255, 15);")
        # 自动锁定窗口
        self.is_locked = True
        # 发送状态变化信号
        self.status_changed.emit("confirmed")
        self.update()  # 触发重绘
    
    def set_edit_mode(self):
        """设置为编辑模式，允许调整位置和大小"""
        log_msg_start = "正在设置答案框为编辑模式..."
        print(log_msg_start) # 保留 print 语句
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'log_message'):
            self.main_window.log_message(log_msg_start)
        elif hasattr(self.parent, 'log_message'): # 后备
            self.parent.log_message(log_msg_start)
        
        # 彻底重置所有锁定状态
        self.is_confirmed = False
        self.is_locked = False
        self.resizing = False
        self.resize_edge = None
        
        # 恢复原来的透明度
        self.centralWidget().setStyleSheet("background-color: rgba(200, 200, 255, 30);")
        
        # 确保鼠标追踪已启用
        self.setMouseTracking(True)
        self.centralWidget().setMouseTracking(True)
        
        # 重置光标为默认
        self.setCursor(Qt.ArrowCursor)
        
        # 发送状态变化信号
        self.status_changed.emit("editing")
        
        # 强制更新UI
        self.update()  # 触发重绘
        
        # 验证状态是否正确设置
        print(f"编辑模式设置完成 - 锁定状态: {self.is_locked}, 确认状态: {self.is_confirmed}")
        if hasattr(self.parent, 'log_message'):
            self.parent.log_message(f"编辑模式设置完成 - 锁定状态: {self.is_locked}, 确认状态: {self.is_confirmed}")
    
    def paintEvent(self, event):
        """绘制窗口边框和提示文字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制边框
        pen = QPen(QColor(255, 0, 0), 2)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        font = QFont("微软雅黑", 10)
        font.setBold(True)
        painter.setFont(font)
        
        # 根据题目显示不同的提示文字
        if self.is_confirmed:
            text1 = f"第{self.question_index}题答案区域已框定" if self.question_index else "答案区域已框定"
            text2 = "学生答案不可被遮挡"
        else:
            text1 = f"此框覆盖第{self.question_index}题学生答案区域" if self.question_index else "请使此框覆盖学生答案"
            text2 = "在配置窗口点击'确认框定'"
        
        # 计算文本宽度以便居中显示
        text1_width = painter.fontMetrics().width(text1)
        text2_width = painter.fontMetrics().width(text2)
        
        # 绘制文字
        painter.setPen(QColor(255, 0, 0, 255))
        combined_text = f"{text1} {text2}"
        combined_width = painter.fontMetrics().width(combined_text)
        combined_x = (self.width() - combined_width) // 2
        painter.drawText(combined_x, 17, combined_text)
    
    def mousePressEvent(self, event):
        """鼠标按下事件，用于移动窗口或调整大小"""
        # 如果窗口已锁定，则忽略鼠标事件
        if self.is_locked:
            return
            
        if event.button() == Qt.LeftButton:
            # 检查是否在边缘
            rect = self.rect()
            pos = event.pos()
            
            # 检测边缘区域
            left_edge = pos.x() <= self.border_width
            right_edge = pos.x() >= rect.width() - self.border_width
            top_edge = pos.y() <= self.border_width
            bottom_edge = pos.y() >= rect.height() - self.border_width
            
            if left_edge or right_edge or top_edge or bottom_edge:
                self.resizing = True
                self.resize_edge = {
                    'left': left_edge,
                    'right': right_edge,
                    'top': top_edge,
                    'bottom': bottom_edge
                }
                event.accept()
            else:
                # 如果不在边缘，则为拖动窗口
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于移动窗口或调整大小"""
        # 如果窗口已锁定，则只更新光标形状为默认
        if self.is_locked:
            self.setCursor(Qt.ArrowCursor)
            return
            
        # 获取鼠标位置
        pos = event.pos()
        rect = self.rect()
        
        # 检测边缘区域
        left_edge = pos.x() <= self.border_width
        right_edge = pos.x() >= rect.width() - self.border_width
        top_edge = pos.y() <= self.border_width
        bottom_edge = pos.y() >= rect.height() - self.border_width
        
        # 根据鼠标位置更新光标形状
        if (left_edge and top_edge) or (right_edge and bottom_edge):
            self.setCursor(Qt.SizeFDiagCursor)  # 左上-右下调整
        elif (right_edge and top_edge) or (left_edge and bottom_edge):
            self.setCursor(Qt.SizeBDiagCursor)  # 右上-左下调整
        elif left_edge or right_edge:
            self.setCursor(Qt.SizeHorCursor)    # 水平调整
        elif top_edge or bottom_edge:
            self.setCursor(Qt.SizeVerCursor)    # 垂直调整
        else:
            self.setCursor(Qt.ArrowCursor)      # 默认光标
        
        # 处理拖动和调整大小
        if self.resizing and event.buttons() & Qt.LeftButton:
            # 调整大小
            global_pos = event.globalPos()
            rect = self.geometry()
            new_rect = QRect(rect)
            
            if self.resize_edge['left']:
                # 调整左边缘
                width_diff = rect.left() - global_pos.x()
                if rect.width() + width_diff >= 50:  # 最小宽度限制
                    new_rect.setLeft(global_pos.x())
            
            if self.resize_edge['right']:
                # 调整右边缘
                new_rect.setRight(global_pos.x())
            
            if self.resize_edge['top']:
                # 调整上边缘
                height_diff = rect.top() - global_pos.y()
                if rect.height() + height_diff >= 50:  # 最小高度限制
                    new_rect.setTop(global_pos.y())
            
            if self.resize_edge['bottom']:
                # 调整下边缘
                new_rect.setBottom(global_pos.y())
            
            # 确保窗口大小不小于最小值
            if new_rect.width() >= 50 and new_rect.height() >= 50:
                self.setGeometry(new_rect)
            
            event.accept()
        
        elif event.buttons() == Qt.LeftButton and not self.resizing:
            # 移动窗口
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.resizing = False
            self.resize_edge = None
            event.accept()
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 窗口显示时，设置为编辑模式
        self.set_edit_mode()
        print("答案框窗口显示事件触发")
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'log_message'): # 检查 main_window
            self.main_window.log_message("答案框窗口显示事件触发")
        elif hasattr(self.parent, 'log_message'):
            self.parent.log_message("答案框窗口显示事件触发")

    def closeEvent(self, event):
        """窗口关闭事件"""
        print("答案框窗口关闭事件触发")
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'log_message'): # 检查 main_window
            self.main_window.log_message("答案框窗口关闭事件触发")
        elif hasattr(self.parent, 'log_message'):
            self.parent.log_message("答案框窗口关闭事件触发")
        # 发送窗口关闭信号
        self.status_changed.emit("closed")
        event.accept()

class QuestionConfigDialog(QDialog):
    """题目配置对话框，用于配置每个题目的评分参数"""
    config_updated = pyqtSignal() # 添加信号
    
    def __init__(self, parent=None, config_manager=None, question_index=1, is_single_q1_mode_active=False):
        super().__init__(parent)
        
        # 设置为非模态对话框，允许同时编辑其他窗口
        self.setModal(False)
        
        self.parent = parent
        self.config_manager = config_manager
        self.question_index = question_index
        self.is_single_q1_mode_active = is_single_q1_mode_active
        
        # 获取当前题目配置
        self.question_config = self.config_manager.get_question_config(question_index) if config_manager else {} # 确保 q_config 是字典

        # 新增三步打分相关UI元素（仅第一题使用）
        self.three_step_scoring_checkbox = None
        self.score_input_group_step1 = None # QGroupBox for step1
        self.score_x_edit_step1 = None
        self.score_y_edit_step1 = None
        self.set_pos_button_step1 = None
        # ... (为 step2 和 step3 添加类似的变量)
        self.score_input_group_step2 = None
        self.score_x_edit_step2 = None
        self.score_y_edit_step2 = None
        self.set_pos_button_step2 = None
        self.score_input_group_step3 = None
        self.score_x_edit_step3 = None
        self.score_y_edit_step3 = None
        self.set_pos_button_step3 = None

        # 原有的单点分数输入组也需要一个引用，方便控制其启用/禁用
        self.original_score_input_group = None
        self.question_type_combo = None # 新增题目类型下拉框成员变量

        # 在 self.init_ui() 之前添加
        self.position_capture_timer = None

        self.init_ui()

        # 初始化UI
    def init_ui(self):
        """初始化UI组件"""
        self.setWindowTitle(f'配置第{self.question_index}题')
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)
        self.resize(400, 500) # 恢复用户指定的固定大小

        # 设置对话框的默认字体
        font = QFont("微软雅黑", 10)
        self.setFont(font)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0) # 设置主布局中各组件的垂直间距为0像素
        
        # --- 1. 分数设置组 ---
        score_group = QGroupBox("注意：本软件固定步长0.5，请确保阅卷网站步长已设为0.5")
        score_group_content_layout = QHBoxLayout() 
        
        score_group_content_layout.addWidget(QLabel("最高分（满分）:"))
        self.max_score_edit = QSpinBox()
        self.max_score_edit.setMinimum(0)
        self.max_score_edit.setMaximum(150)
        self.max_score_edit.setValue(self.question_config.get('max_score', 150) if self.question_config else 150)
        score_group_content_layout.addWidget(self.max_score_edit)
        score_group_content_layout.addSpacing(50) # 添加伸缩空间
        
        score_group_content_layout.addWidget(QLabel("最低分:"))
        self.min_score_edit = QSpinBox()
        self.min_score_edit.setMinimum(0)
        self.min_score_edit.setMaximum(150)
        self.min_score_edit.setValue(self.question_config.get('min_score', 0) if self.question_config else 0)
        score_group_content_layout.addWidget(self.min_score_edit)
        
        score_group.setLayout(score_group_content_layout)
        main_layout.addWidget(score_group)

        # --- 新增：题目类型选择 ---
        question_type_group = QGroupBox("选择题目类型（重要）") # 可以给它一个组标题
        question_type_layout = QHBoxLayout()

        self.question_type_combo = QComboBox()
        # 定义题目类型选项 (键: 内部标识符, 值: UI显示文本)
        self.question_types_map = {
            "Subjective_PointBased_QA": "主观题-按点给分，强调答案命中得分点",
            "Objective_FillInTheBlank": "较客观的主观题-填空题",
            "Formula_Proof_StepBased": "理科公式计算/证明题：强调步骤、逻辑、符号规范",
            "Holistic_Evaluation_Open": "文科开放题-依据评分细则中的宏观标准进行综合判断"
        }
        for display_text in self.question_types_map.values():
            self.question_type_combo.addItem(display_text)

        # 加载当前配置的题目类型
        current_type_identifier = self.question_config.get('question_type', 'Subjective_PointBased_QA')
        current_display_text = "主观题-按点给分" # 默认显示
        for identifier, display in self.question_types_map.items():
            if identifier == current_type_identifier:
                current_display_text = display
                break

        current_index = self.question_type_combo.findText(current_display_text)
        if current_index != -1:
            self.question_type_combo.setCurrentIndex(current_index)

        question_type_layout.addWidget(self.question_type_combo)
        question_type_group.setLayout(question_type_layout)
        main_layout.addWidget(question_type_group)
        # --- 结束新增 ---

        # --- 2. 分数输入位置设置 ---
        # 使用辅助函数重构，以保持UI统一
        input_group = self._create_position_input_group(
            "设置分数输入位置",
            'score_x_edit',
            'score_y_edit',
            'set_pos_button', # 此属性将在辅助函数中动态创建
            "分数输入"
        )
        main_layout.addWidget(input_group)
        self.original_score_input_group = input_group

        # --- 3. 三步分数输入模式 (仅第一题) ---
        if self.question_index == 1:
            three_step_group = QGroupBox("")
            three_step_group_main_layout = QVBoxLayout() 

            self.three_step_scoring_checkbox = QCheckBox("启用 最终得分分成三份 输入三个位置 (仅第一题生效）")
            enable_three_step_from_config = self.question_config.get('enable_three_step_scoring', False)
            self.three_step_scoring_checkbox.setChecked(enable_three_step_from_config)

            self.three_step_scoring_checkbox.stateChanged.connect(self.toggle_three_step_mode_ui)
            three_step_group_main_layout.addWidget(self.three_step_scoring_checkbox)

            # 使用新的辅助函数创建三个步骤的输入组
            self.score_input_group_step1 = self._create_position_input_group(
                "设置位置 1", 'score_x_edit_step1', 'score_y_edit_step1', 'set_pos_button_step1', "位置 1"
            )
            three_step_group_main_layout.addWidget(self.score_input_group_step1)

            self.score_input_group_step2 = self._create_position_input_group(
                "设置位置 2", 'score_x_edit_step2', 'score_y_edit_step2', 'set_pos_button_step2', "位置 2"
            )
            three_step_group_main_layout.addWidget(self.score_input_group_step2)

            self.score_input_group_step3 = self._create_position_input_group(
                "设置位置 3", 'score_x_edit_step3', 'score_y_edit_step3', 'set_pos_button_step3', "位置 3"
            )
            three_step_group_main_layout.addWidget(self.score_input_group_step3)

            if not self.is_single_q1_mode_active:
                self.three_step_scoring_checkbox.setChecked(False)
                self.three_step_scoring_checkbox.setEnabled(False)

            # 确保在所有相关UI元素创建并赋值后调用
            self.toggle_three_step_mode_ui(enable_three_step_from_config)

            three_step_group.setLayout(three_step_group_main_layout)
            
            original_input_group_index = -1
            for i in range(main_layout.count()):
                widget_item = main_layout.itemAt(i)
                if widget_item and widget_item.widget() == self.original_score_input_group:
                    original_input_group_index = i
                    break
            if original_input_group_index != -1:
                main_layout.insertWidget(original_input_group_index + 1, three_step_group)
            else: 
                main_layout.addWidget(three_step_group)


        # --- 4. 提交按钮位置设置 ---
        submit_group = QGroupBox("提交按钮位置设置")
        submit_group_content_layout = QHBoxLayout() 
        
        submit_group_content_layout.addWidget(QLabel("坐标:"))
        submit_group_content_layout.addWidget(QLabel("X:"))
        self.submit_x_edit = QLineEdit()
        submit_pos_val = self.question_config.get('confirm_button_pos') if self.question_config else None
        submit_x, submit_y = submit_pos_val if submit_pos_val is not None else (0, 0)
        self.submit_x_edit.setText(str(submit_x))
        submit_group_content_layout.addWidget(self.submit_x_edit)
        
        submit_group_content_layout.addWidget(QLabel("Y:"))
        self.submit_y_edit = QLineEdit()
        self.submit_y_edit.setText(str(submit_y))
        submit_group_content_layout.addWidget(self.submit_y_edit)
        
        set_submit_button = QPushButton("设置提交按钮位置")
        set_submit_button.clicked.connect(lambda: self.set_position('submit_x_edit', 'submit_y_edit', "提交按钮"))
        submit_group_content_layout.addWidget(set_submit_button)
        
        submit_group.setLayout(submit_group_content_layout)
        main_layout.addWidget(submit_group)
        
        # --- 5. 翻页按钮配置 ---
        next_group = QGroupBox("")
        next_group_main_layout = QVBoxLayout() 
        
        self.enable_next_check = QCheckBox("启用翻页按钮")
        enable_next_button_for_current_q = self.question_config.get('enable_next_button', False) if self.question_config else False
        self.enable_next_check.setChecked(enable_next_button_for_current_q)
        self.enable_next_check.stateChanged.connect(self.toggle_next_button_fields)
        next_group_main_layout.addWidget(self.enable_next_check) 
        
        next_coord_and_button_layout = QHBoxLayout() 
        next_coord_and_button_layout.addWidget(QLabel("坐标:"))
        next_coord_and_button_layout.addWidget(QLabel("X:"))
        self.next_x_edit = QLineEdit()
        next_pos_val = self.question_config.get('next_button_pos') if self.question_config else None
        current_next_x, current_next_y = next_pos_val if next_pos_val is not None else (0, 0)
        self.next_x_edit.setText(str(current_next_x))
        next_coord_and_button_layout.addWidget(self.next_x_edit)
        
        next_coord_and_button_layout.addWidget(QLabel("Y:"))
        self.next_y_edit = QLineEdit()
        self.next_y_edit.setText(str(current_next_y))
        next_coord_and_button_layout.addWidget(self.next_y_edit)
        
        self.set_next_button = QPushButton("设置翻页按钮位置")
        self.set_next_button.clicked.connect(lambda: self.set_position('next_x_edit', 'next_y_edit', "翻页按钮"))
        next_coord_and_button_layout.addWidget(self.set_next_button)
        
        next_group_main_layout.addLayout(next_coord_and_button_layout)
        next_group.setLayout(next_group_main_layout)
        main_layout.addWidget(next_group)
        
        self.toggle_next_button_fields(self.enable_next_check.isChecked()) 
        
        # --- 6. 答案区域配置 (恢复到旧版对称布局) ---
        answer_group = QGroupBox("") # 确保 answer_group 已定义
        answer_group_main_layout = QVBoxLayout()

        # 先获取 answer_area，如果为 None 则使用空字典作为后备
        answer_area_config = self.question_config.get('answer_area') if self.question_config else None
        if answer_area_config is None:
            answer_area_config = {} # 使用空字典，这样后续的 .get 调用不会出错

        # 左上角坐标行
        answer_coord_layout_tl = QHBoxLayout() 
        answer_coord_layout_tl.addWidget(QLabel("左上角 X:"))
        self.answer_x1_edit = QLineEdit()
        answer_x1 = answer_area_config.get('x1', 0) # 直接从 answer_area_config 获取
        self.answer_x1_edit.setText(str(answer_x1))
        answer_coord_layout_tl.addWidget(self.answer_x1_edit)
        
        answer_coord_layout_tl.addWidget(QLabel("Y:"))
        self.answer_y1_edit = QLineEdit()
        answer_y1 = answer_area_config.get('y1', 0)
        self.answer_y1_edit.setText(str(answer_y1))
        answer_coord_layout_tl.addWidget(self.answer_y1_edit)
        answer_group_main_layout.addLayout(answer_coord_layout_tl)
        
        # 右下角坐标行
        answer_coord_layout_br = QHBoxLayout() 
        answer_coord_layout_br.addWidget(QLabel("右下角 X:"))
        self.answer_x2_edit = QLineEdit()
        answer_x2 = answer_area_config.get('x2', 0)
        self.answer_x2_edit.setText(str(answer_x2))
        answer_coord_layout_br.addWidget(self.answer_x2_edit)
        
        answer_coord_layout_br.addWidget(QLabel("Y:"))
        self.answer_y2_edit = QLineEdit()
        answer_y2 = answer_area_config.get('y2', 0)
        self.answer_y2_edit.setText(str(answer_y2))
        answer_coord_layout_br.addWidget(self.answer_y2_edit)
        answer_group_main_layout.addLayout(answer_coord_layout_br)

        # 按钮占据可用水平空间 (这部分不变)
        answer_button_layout = QHBoxLayout()
        self.set_answer_button = QPushButton("框定答案区域")
        self.set_answer_button.clicked.connect(self.start_answer_area_selection)
        answer_button_layout.addWidget(self.set_answer_button)
        answer_group_main_layout.addLayout(answer_button_layout)
        
        answer_group.setLayout(answer_group_main_layout)
        main_layout.addWidget(answer_group) # 确保 answer_group 被添加到主布局
        
        # --- 7. 按钮区域 (Save, Cancel) ---
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_config)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

        # 由于设置了固定的 resize，adjustSize() 和 setMinimumWidth() 通常不再需要，
        # 或者其效果会被 resize 覆盖。
        # self.adjustSize() 
        # current_width = self.width()
        # self.setMinimumWidth(max(600, current_width))

    def _create_position_input_group(self, title, x_edit_attr, y_edit_attr, button_attr, pos_name):
        """辅助函数：创建一个用于设置坐标的位置输入UI组。"""
        # 创建UI组件
        group_box = QGroupBox("") # 组的标题由外部QLabel提供，保持UI一致性
        layout = QHBoxLayout()
        
        x_edit = QLineEdit()
        y_edit = QLineEdit()
        set_button = QPushButton(title)

        # 将创建的控件设置为类的成员变量，以便后续访问
        setattr(self, x_edit_attr, x_edit)
        setattr(self, y_edit_attr, y_edit)
        setattr(self, button_attr, set_button)

        # 布局
        layout.addWidget(QLabel("X:"))
        layout.addWidget(x_edit)
        layout.addWidget(QLabel("Y:"))
        layout.addWidget(y_edit)
        layout.addWidget(set_button)
        group_box.setLayout(layout)

        # 从配置加载初始值
        # 注意：这里的逻辑依赖于config中key的命名与属性名的某种关联
        # 例如 x_edit_attr = 'score_x_edit_step1' 对应 config key 'score_input_pos_step1'
        config_key = f"score_input_pos_{pos_name.split(' ')[-1]}" # 从 '位置 1' 中提取 '1'
        if pos_name == "分数输入": # 特殊处理默认的分数输入组
            config_key = "score_input_pos"
            
        pos_val = self.question_config.get(config_key)
        pos_x, pos_y = pos_val if pos_val is not None else (0, 0)
        x_edit.setText(str(pos_x))
        y_edit.setText(str(pos_y))

        # 连接信号
        # 使用 setattr 来动态地引用成员变量名
        set_button.clicked.connect(lambda: self.set_position(x_edit_attr, y_edit_attr, f"{pos_name}"))

        return group_box

    def toggle_next_button_fields(self, checked):
        """切换翻页按钮字段的启用状态"""
        self.next_x_edit.setEnabled(checked)
        self.next_y_edit.setEnabled(checked)
        self.set_next_button.setEnabled(checked)

    def start_answer_area_selection(self):
        """开始框定答案区域"""
        try:
            # 获取当前题目的专用答案框窗口
            answer_window = self.parent.get_or_create_answer_window(self.question_index)

            # 显示窗口
            answer_window.show()
            answer_window.set_edit_mode()
            answer_window.raise_()
            answer_window.activateWindow()

            self.parent.log_message(f"请调整第{self.question_index}题的答案框位置和大小")

            # 更新按钮状态
            self.set_answer_button.clicked.disconnect()
            self.set_answer_button.clicked.connect(
                lambda: self.confirm_answer_area_selection(answer_window)
            )
            self.set_answer_button.setText("确认框定")
            self.set_answer_button.setStyleSheet("background-color: #FF5555; color: white; font-weight: bold;")
        except Exception as e:
            self.parent.log_message(f"框定第{self.question_index}题答案区域出错: {str(e)}", is_error=True)

    def confirm_answer_area_selection(self, answer_window):
        """确认框定答案区域"""
        try:
            screen_pos = answer_window.geometry().topLeft()
            x1 = int(screen_pos.x())
            y1 = int(screen_pos.y())
            x2 = answer_window.geometry().width() + x1
            y2 = answer_window.geometry().height() + y1

            # 更新坐标显示
            self.answer_x1_edit.setText(str(x1))
            self.answer_y1_edit.setText(str(y1))
            self.answer_x2_edit.setText(str(x2))
            self.answer_y2_edit.setText(str(y2))

            self.capture_answer_area(x1, y1, x2, y2)

            self.parent.log_message(f"第{self.question_index}题答案区域已框定: ({x1}, {y1}) - ({x2}, {y2})")

            # 恢复按钮状态
            self.set_answer_button.clicked.disconnect()
            self.set_answer_button.clicked.connect(self.start_answer_area_selection)
            self.set_answer_button.setText("重新框定答案区域")
            self.set_answer_button.setStyleSheet("")

            # 设置为已确认模式
            answer_window.set_confirmed_mode()
        except Exception as e:
            self.parent.log_message(f"确认第{self.question_index}题答案区域出错: {str(e)}", is_error=True)

    def capture_answer_area(self, x1, y1, x2, y2):
        """捕获答案区域的屏幕截图或处理坐标"""
        try:
            # 这里可以添加逻辑来捕获屏幕截图或其他处理
            # 目前作为占位符，确保方法存在
            self.parent.log_message(f"答案区域坐标已处理: ({x1}, {y1}) - ({x2}, {y2})")
        except Exception as e:
            self.parent.log_message(f"处理答案区域坐标出错: {str(e)}", is_error=True)

    def set_position(self, x_edit_name, y_edit_name, position_name):
        """设置位置坐标"""
        try:
            # 创建一个提示标签，显示在对话框顶部
            if not hasattr(self, 'instruction_label'):
                self.instruction_label = QLabel("")
                # 将标签插入到布局的顶部（索引为0，确保在最顶端）
                self.layout().insertWidget(0, self.instruction_label)

            self.instruction_label.setText(f"请将鼠标移动到{position_name}位置，5秒后将自动捕获位置...")
            self.instruction_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
            self.parent.log_message(f"请将鼠标移动到{position_name}位置，5秒后将自动捕获位置...")

            # 使用定时器模拟等待5秒
            # 创建一个全新的定时器实例以确保信号连接正确
            self.position_capture_timer = QTimer(self)
            self.position_capture_timer.setSingleShot(True)
            self.position_capture_timer.timeout.connect(lambda: self.capture_position(x_edit_name, y_edit_name, position_name))
            self.position_capture_timer.start(5000)

        except Exception as e:
            self.parent.log_message(f"设置{position_name}位置出错: {str(e)}", is_error=True)
            if hasattr(self, 'instruction_label'):
                self.instruction_label.setText("")

    def capture_position(self, x_edit_name, y_edit_name, position_name):
        """捕获鼠标位置并更新文本框"""
        try:
            # 获取当前鼠标位置
            x, y = pyautogui.position()

            # 设置坐标到文本框
            x_edit = getattr(self, x_edit_name)
            y_edit = getattr(self, y_edit_name)
            x_edit.setText(str(x))
            y_edit.setText(str(y))

            # 更新提示信息
            if hasattr(self, 'instruction_label'):
                self.instruction_label.setText(f"{position_name}位置已捕获: ({x}, {y})")
            self.parent.log_message(f"{position_name}位置已设置为: ({x}, {y})")
            self.position_capture_timer = None # 任务完成，清理引用
        except Exception as e:
            self.parent.log_message(f"捕获{position_name}位置出错: {str(e)}", is_error=True)
            if hasattr(self, 'instruction_label'):
                self.instruction_label.setText("")

    def save_config(self):
        """保存配置"""
        try:
            # 获取分数设置
            max_score = self.max_score_edit.value()
            min_score = self.min_score_edit.value()

            # 获取分数输入位置
            score_x = int(self.score_x_edit.text())
            score_y = int(self.score_y_edit.text())

            # 获取提交按钮位置
            submit_x = int(self.submit_x_edit.text())
            submit_y = int(self.submit_y_edit.text())

            # 获取答案区域位置
            answer_x1 = int(self.answer_x1_edit.text())
            answer_y1 = int(self.answer_y1_edit.text())
            answer_x2 = int(self.answer_x2_edit.text())
            answer_y2 = int(self.answer_y2_edit.text())

            # --- 新增：获取并保存题目类型 ---
            selected_display_text = self.question_type_combo.currentText()
            selected_type_identifier = 'Subjective_PointBased_QA' # 默认值
            for identifier, display in self.question_types_map.items(): # self.question_types_map 在 init_ui 中定义
                if display == selected_display_text:
                    selected_type_identifier = identifier
                    break
            # --- 结束新增 ---

            # 更新题目配置
            if self.config_manager:
                self.config_manager.update_question_config(str(self.question_index), 'max_score', max_score)
                self.config_manager.update_question_config(str(self.question_index), 'min_score', min_score)
                self.config_manager.update_question_config(str(self.question_index), 'score_input_pos', (score_x, score_y))
                self.config_manager.update_question_config(str(self.question_index), 'confirm_button_pos', (submit_x, submit_y))
                self.config_manager.update_question_config(str(self.question_index), 'question_type', selected_type_identifier) # 保存题目类型
                self.config_manager.update_question_config(str(self.question_index), 'answer_area', {
                    'x1': answer_x1,
                    'y1': answer_y1,
                    'x2': answer_x2,
                    'y2': answer_y2
                })

            # 更新当前小题的翻页按钮配置
            enable_next_for_current_q = self.enable_next_check.isChecked()
            self.config_manager.update_question_config(str(self.question_index), 'enable_next_button', enable_next_for_current_q)

            if enable_next_for_current_q:
                try:
                    current_q_next_x = int(self.next_x_edit.text())
                    current_q_next_y = int(self.next_y_edit.text())
                    self.config_manager.update_question_config(str(self.question_index), 'next_button_pos', (current_q_next_x, current_q_next_y))
                except ValueError:
                    # 如果坐标无效，则保存为 None，并记录日志或提示用户
                    self.config_manager.update_question_config(str(self.question_index), 'next_button_pos', None)
                    if self.parent and hasattr(self.parent, 'log_message'):
                        self.parent.log_message(f"警告: 第{self.question_index}题的翻页按钮坐标无效，未保存。", is_error=True)
            else:
                self.config_manager.update_question_config(str(self.question_index), 'next_button_pos', None)

            # --- 开始保存三步打分相关配置 (仅第一题) ---
            if self.question_index == 1 and self.three_step_scoring_checkbox: # 确保复选框已创建
                is_three_step_enabled = self.three_step_scoring_checkbox.isChecked()
                self.config_manager.update_question_config(str(self.question_index), 'enable_three_step_scoring', is_three_step_enabled) # 使用 str(self.question_index)

                if is_three_step_enabled:
                    try:
                        pos_s1_x = int(self.score_x_edit_step1.text())
                        pos_s1_y = int(self.score_y_edit_step1.text())
                        self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step1', (pos_s1_x, pos_s1_y))
                    except ValueError:
                        self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step1', None)
                        if self.parent: self.parent.log_message(f"警告: 第{self.question_index}题三步打分位置1坐标无效", True)

                    try:
                        pos_s2_x = int(self.score_x_edit_step2.text())
                        pos_s2_y = int(self.score_y_edit_step2.text())
                        self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step2', (pos_s2_x, pos_s2_y))
                    except ValueError:
                        self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step2', None)
                        if self.parent: self.parent.log_message(f"警告: 第{self.question_index}题三步打分位置2坐标无效", True)

                    try:
                        pos_s3_x = int(self.score_x_edit_step3.text())
                        pos_s3_y = int(self.score_y_edit_step3.text())
                        self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step3', (pos_s3_x, pos_s3_y))
                    except ValueError:
                        self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step3', None)
                        if self.parent: self.parent.log_message(f"警告: 第{self.question_index}题三步打分位置3坐标无效", True)
                else:
                    # 如果未启用，可以选择清除这些位置或保持原样
                    # 为了简单，可以不清除，ConfigManager在加载时会处理None
                    # 或者明确设为None:
                    self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step1', None)
                    self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step2', None)
                    self.config_manager.update_question_config(str(self.question_index), 'score_input_pos_step3', None)
            # --- 结束保存三步打分相关配置 ---

            self.parent.log_message(f"第{self.question_index}题配置已保存")
            log_enable_next_status = self.config_manager.get_question_config(self.question_index).get('enable_next_button', False)
            self.parent.log_message(f"第{self.question_index}题翻页按钮状态: {'启用' if log_enable_next_status else '禁用'}")
            self.parent.log_message(f"答案区域已配置: ({answer_x1}, {answer_y1}) - ({answer_x2}, {answer_y2})")

            # 发射信号通知配置已更新，由MainWindow负责保存到文件
            self.config_updated.emit()

            self.accept()
        except Exception as e:
            self.parent.log_message(f"保存配置出错: {str(e)}", is_error=True)

    def toggle_three_step_mode_ui(self, checked):
        """根据三步打分模式复选框状态，切换UI元素的启用/禁用"""
        if self.question_index == 1: # 确保只对第一题操作
            # 切换原有单点分数输入组的启用状态
            if self.original_score_input_group:
                self.original_score_input_group.setEnabled(not checked)

            # 切换三个新分数输入位置组的启用状态
            if self.score_input_group_step1:
                self.score_input_group_step1.setEnabled(checked)
            if self.score_input_group_step2:
                self.score_input_group_step2.setEnabled(checked)
            if self.score_input_group_step3:
                self.score_input_group_step3.setEnabled(checked)
        else: # 如果不是第一题，确保三步打分相关UI是禁用的（理论上不应显示）
            if self.score_input_group_step1: self.score_input_group_step1.setEnabled(False)
            if self.score_input_group_step2: self.score_input_group_step2.setEnabled(False)
            if self.score_input_group_step3: self.score_input_group_step3.setEnabled(False)
            if self.original_score_input_group: self.original_score_input_group.setEnabled(True)
