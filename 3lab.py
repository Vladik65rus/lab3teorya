import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import re

# ==================== ЛЕКСИЧЕСКИЙ АНАЛИЗАТОР ====================
class LexicalAnalyzer:
    """Лексический анализатор для Rust"""
    
    def __init__(self):
        self.tokens = []
        self.errors = []
        
    def analyze(self, text):
        self.tokens = []
        self.errors = []
        
        lines = text.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._analyze_line(line, line_num)
        
        return self.tokens, self.errors
    
    def _analyze_line(self, line, line_num):
        i = 0
        n = len(line)
        
        while i < n:
            c = line[i]
            
            if c.isspace():
                i += 1
                continue
            
            if c.isalpha():
                start = i
                while i < n and (line[i].isalnum() or line[i] == '_'):
                    i += 1
                word = line[start:i]
                self._add_token(word, line_num, start+1, i)
                continue
            
            if c.isdigit():
                start = i
                while i < n and line[i].isdigit():
                    i += 1
                number = line[start:i]
                self.tokens.append({
                    'type': 'NUMBER',
                    'value': number,
                    'line': line_num,
                    'start': start+1,
                    'end': i
                })
                continue
            
            token_map = {
                '=': 'ASSIGN',
                '+': 'PLUS',
                '-': 'MINUS',
                '*': 'MULTIPLY',
                '/': 'DIVIDE',
                '(': 'LPAREN',
                ')': 'RPAREN',
                '{': 'LBRACE',
                '}': 'RBRACE',
                ';': 'SEMICOLON',
                ',': 'COMMA',
                ':': 'COLON',
                '>': 'ARROW'
            }
            
            if c in token_map:
                self.tokens.append({
                    'type': token_map[c],
                    'value': c,
                    'line': line_num,
                    'start': i+1,
                    'end': i+1
                })
                i += 1
            else:
                self.errors.append({
                    'type': 'LEXICAL_ERROR',
                    'value': c,
                    'line': line_num,
                    'start': i+1,
                    'end': i+1,
                    'message': f"Недопустимый символ '{c}'"
                })
                i += 1
    
    def _add_token(self, word, line_num, start, end):
        keywords = {'fn', 'return'}
        types = {'i32', 'i64', 'f32', 'f64', 'bool'}
        
        if word in keywords:
            token_type = 'KEYWORD'
        elif word in types:
            token_type = 'TYPE'
        else:
            token_type = 'IDENTIFIER'
        
        self.tokens.append({
            'type': token_type,
            'value': word,
            'line': line_num,
            'start': start,
            'end': end
        })


# ==================== СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР ====================
class SyntaxAnalyzer:
    """Синтаксический анализатор с методом Айронса (Rust)"""
    
    # Грамматика:
    # S -> fn id ( P ) -> T { return E } ;
    # P -> id : T | id : T , P
    # T -> i32 | i64 | f32 | f64 | bool
    # E -> id | number | ( E ) | E + E | E - E | E * E | E / E
    
    def __init__(self):
        self.tokens = []
        self.pos = 0
        self.errors = []
        
    def parse(self, tokens):
        """Основной метод синтаксического анализа"""
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        
        if not tokens:
            self.errors.append({
                'fragment': 'пустая строка',
                'line': 1,
                'pos': 1,
                'message': 'Пустой ввод'
            })
            return self.errors
        
        # Запуск анализа
        self._S()
        
        # Проверка, что все токены обработаны
        if self.pos < len(self.tokens) and not self.errors:
            token = self.tokens[self.pos]
            self.errors.append({
                'fragment': token['value'],
                'line': token['line'],
                'pos': token['start'],
                'message': f'Лишний токен "{token["value"]}" после завершения программы'
            })
        
        return self.errors
    
    def _current_token(self):
        """Возвращает текущий токен"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _match(self, expected_type, expected_value=None):
        """Сопоставляет текущий токен с ожидаемым"""
        token = self._current_token()
        if not token:
            return False
        
        if token['type'] == expected_type:
            if expected_value is None or token['value'] == expected_value:
                self.pos += 1
                return True
        
        return False
    
    def _add_error(self, expected, found):
        """Добавляет ошибку в список"""
        token = self._current_token()
        if token:
            line = token['line']
            pos = token['start']
            fragment = token['value']
            message = f'Ожидалось "{expected}", найдено "{fragment}"'
        else:
            line = 1
            pos = 1
            fragment = 'конец строки'
            message = f'Ожидалось "{expected}", достигнут конец ввода'
        
        self.errors.append({
            'fragment': fragment,
            'line': line,
            'pos': pos,
            'message': message
        })
    
    # ==================== НЕТЕРМИНАЛЫ ====================
    
    def _S(self):
        """S -> fn id ( P ) -> T { return E } ;"""
        
        # fn
        if not self._match('KEYWORD', 'fn'):
            self._add_error('fn', self._current_token()['value'] if self._current_token() else 'EOF')
            # Метод Айронса: пропускаем до следующего 'fn' или конца
            while self._current_token() and self._current_token()['type'] != 'KEYWORD':
                self.pos += 1
            if self._current_token() and self._current_token()['value'] == 'fn':
                self.pos += 1
            else:
                return
        
        # id
        if not self._match('IDENTIFIER'):
            self._add_error('идентификатор', self._current_token()['value'] if self._current_token() else 'EOF')
            while self._current_token() and self._current_token()['type'] not in ['LPAREN', 'LBRACE']:
                self.pos += 1
        
        # (
        if not self._match('LPAREN'):
            self._add_error('(', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # P - параметры
        if self._current_token() and self._current_token()['type'] != 'RPAREN':
            self._P()
        
        # )
        if not self._match('RPAREN'):
            self._add_error(')', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # ->
        # Проверяем последовательность '-' и '>'
        if self._current_token() and self._current_token()['type'] == 'MINUS':
            self.pos += 1
            if not self._match('ARROW'):
                self._add_error('->', self._current_token()['value'] if self._current_token() else 'EOF')
        else:
            self._add_error('->', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # T - тип возврата
        self._T()
        
        # {
        if not self._match('LBRACE'):
            self._add_error('{', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # return
        if not self._match('KEYWORD', 'return'):
            self._add_error('return', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # E - выражение
        self._E()
        
        # }
        if not self._match('RBRACE'):
            self._add_error('}', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # ;
        if not self._match('SEMICOLON'):
            self._add_error(';', self._current_token()['value'] if self._current_token() else 'EOF')
    
    def _P(self):
        """P -> id : T | id : T , P"""
        
        # id
        if not self._match('IDENTIFIER'):
            self._add_error('идентификатор', self._current_token()['value'] if self._current_token() else 'EOF')
            return
        
        # :
        if not self._match('COLON'):
            self._add_error(':', self._current_token()['value'] if self._current_token() else 'EOF')
        
        # T - тип
        self._T()
        
        # , P
        if self._current_token() and self._current_token()['type'] == 'COMMA':
            self.pos += 1  # пропускаем ','
            self._P()
    
    def _T(self):
        """T -> i32 | i64 | f32 | f64 | bool"""
        token = self._current_token()
        if token and token['type'] == 'TYPE':
            self.pos += 1
        else:
            self._add_error('тип данных (i32, i64, f32, f64, bool)', 
                           token['value'] if token else 'EOF')
    
    def _E(self):
        """E -> id | number | ( E ) | E + E | E - E | E * E | E / E"""
        
        token = self._current_token()
        if not token:
            self._add_error('выражение', 'EOF')
            return
        
        # id или number
        if token['type'] in ['IDENTIFIER', 'NUMBER']:
            self.pos += 1
        
        # ( E )
        elif token['type'] == 'LPAREN':
            self.pos += 1  # пропускаем '('
            self._E()
            if not self._match('RPAREN'):
                self._add_error(')', self._current_token()['value'] if self._current_token() else 'EOF')
        
        else:
            self._add_error('выражение (идентификатор, число или скобки)', token['value'])
            return
        
        # Обработка операторов E + E | E - E | E * E | E / E
        if self._current_token() and self._current_token()['type'] in ['PLUS', 'MINUS', 'MULTIPLY', 'DIVIDE']:
            self.pos += 1  # пропускаем оператор
            self._E()


# ==================== ПОИСК ПО РЕГУЛЯРНЫМ ВЫРАЖЕНИЯМ ====================
class RegexSearcher:
    """Класс для поиска подстрок с помощью регулярных выражений"""
    
    def __init__(self):
        self.results = []
        
    def search_hex_color(self, text):
        pattern = r'#[0-9A-Fa-f]{3}\b'
        return self._search_pattern(text, pattern, "HEX цвет (3 символа)")
    
    def search_identifier(self, text):
        pattern = r'[a-zA-Z$_][a-zA-Z0-9]*\b'
        return self._search_pattern(text, pattern, "Идентификатор")
    
    def search_date(self, text):
        pattern = r'(?:(?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/(?:19|20)\d{2})'
        matches = self._search_pattern(text, pattern, "Дата MM/DD/YYYY")
        valid_matches = []
        for match in matches:
            if self._validate_date(match['match']):
                valid_matches.append(match)
            else:
                match['type'] = "❌ Некорректная дата"
                valid_matches.append(match)
        return valid_matches
    
    def _search_pattern(self, text, pattern, type_name):
        results = []
        compiled = re.compile(pattern, re.IGNORECASE)
        
        for match in compiled.finditer(text):
            start = match.start()
            end = match.end()
            matched_text = match.group()
            
            line_num = text[:start].count('\n') + 1
            last_newline = text[:start].rfind('\n')
            col_num = start - last_newline if last_newline != -1 else start + 1
            
            results.append({
                'type': type_name,
                'match': matched_text,
                'line': line_num,
                'col': col_num,
                'start': start,
                'end': end
            })
        
        return results
    
    def _validate_date(self, date_str):
        try:
            month, day, year = map(int, date_str.split('/'))
            if month < 1 or month > 12:
                return False
            days_in_month = [31, 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28,
                            31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day < 1 or day > days_in_month[month - 1]:
                return False
            return True
        except:
            return False


# ==================== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ====================
class TextEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Языковой процессор - Вариант 75 (Rust)")
        self.root.geometry("1300x850")
        self.root.configure(bg='#f0f0f0')
        
        self.current_file = None
        self.text_changed = False
        self.lexical_analyzer = LexicalAnalyzer()
        self.syntax_analyzer = SyntaxAnalyzer()
        self.regex_searcher = RegexSearcher()
        self.current_matches = []
        
        self.setup_ui()
        self.bind_events()
        
    def bind_events(self):
        self.text_editor.bind('<<Modified>>', self.on_text_modified)
        self.syntax_editor.bind('<<Modified>>', self.on_syntax_modified)
        self.regex_editor.bind('<<Modified>>', self.on_regex_modified)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_text_modified(self, event=None):
        if self.text_editor.edit_modified():
            self.text_changed = True
            self.text_editor.edit_modified(False)
    
    def on_syntax_modified(self, event=None):
        if self.syntax_editor.edit_modified():
            self.text_changed = True
            self.syntax_editor.edit_modified(False)
    
    def on_regex_modified(self, event=None):
        if self.regex_editor.edit_modified():
            self.text_changed = True
            self.regex_editor.edit_modified(False)
            
    def on_closing(self):
        if self.text_changed:
            result = messagebox.askyesnocancel("Выход", "Сохранить изменения?")
            if result is None:
                return
            elif result:
                self.save_file()
        self.root.destroy()
        
    def setup_ui(self):
        self.create_menu()
        self.create_toolbar()
        
        # Создаем вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка 1: Лексический анализатор
        self.lexical_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.lexical_frame, text="📝 Лексический анализатор")
        self.setup_lexical_tab()
        
        # Вкладка 2: Синтаксический анализатор
        self.syntax_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.syntax_frame, text="🔧 Синтаксический анализатор")
        self.setup_syntax_tab()
        
        # Вкладка 3: Поиск по регулярным выражениям
        self.regex_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.regex_frame, text="🔍 Поиск по регулярным выражениям")
        self.setup_regex_tab()
        
        self.create_status_bar()
    
    def setup_lexical_tab(self):
        """Вкладка с лексическим анализатором"""
        main_frame = tk.Frame(self.lexical_frame, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        top_panel = tk.Frame(main_frame, bg='#f0f0f0')
        top_panel.pack(fill=tk.X, pady=5)
        
        start_btn = tk.Button(top_panel, text="▶ ЛЕКСИЧЕСКИЙ АНАЛИЗ", command=self.analyze_lexical,
                              bg='#F44336', fg='white', font=('Arial', 12, 'bold'),
                              relief=tk.RAISED, bd=3, width=20, height=1)
        start_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        clear_btn = tk.Button(top_panel, text="🗑 ОЧИСТИТЬ", command=self.clear_lexical_results,
                              bg='#607D8B', fg='white', font=('Arial', 10, 'bold'),
                              relief=tk.RAISED, bd=2, width=12)
        clear_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        editor_frame = tk.LabelFrame(main_frame, text="📝 Редактор (введите код Rust):", 
                                      font=("Arial", 10, "bold"), bg='#ffffff')
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.lexical_modified_label = tk.Label(editor_frame, text="", bg='#ffffff', fg='#ff0000')
        self.lexical_modified_label.pack(anchor='ne', padx=5, pady=2)
        
        self.text_editor = scrolledtext.ScrolledText(
            editor_frame, wrap=tk.WORD, font=("Courier New", 11),
            undo=True, background='#ffffff', foreground='#000000',
            insertbackground='#000000', selectbackground='#c0c0c0',
            padx=5, pady=5, height=12
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        example_text = """fn calc(a: i32, b: i32) -> i32 {
    return a + b
}"""
        self.text_editor.insert("1.0", example_text)
        
        result_frame = tk.LabelFrame(main_frame, text="📊 Результаты лексического анализа:", 
                                      font=("Arial", 10, "bold"), bg='#ffffff')
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('code', 'type', 'lexeme', 'position')
        self.lexical_table = ttk.Treeview(result_frame, columns=columns, show='headings', height=8)
        
        self.lexical_table.heading('code', text='🔢 Код')
        self.lexical_table.heading('type', text='🏷 Тип')
        self.lexical_table.heading('lexeme', text='📄 Лексема')
        self.lexical_table.heading('position', text='📍 Позиция')
        
        self.lexical_table.column('code', width=70, anchor='center')
        self.lexical_table.column('type', width=250, anchor='w')
        self.lexical_table.column('lexeme', width=120, anchor='center')
        self.lexical_table.column('position', width=200, anchor='center')
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.lexical_table.yview)
        self.lexical_table.configure(yscrollcommand=scrollbar.set)
        
        self.lexical_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lexical_error_label = tk.Label(result_frame, text="❌ Ошибок: 0", 
                                             font=("Arial", 9, "bold"),
                                             bg='#ffffff', fg='#F44336')
        self.lexical_error_label.pack(side=tk.BOTTOM, pady=3)
    
    def setup_syntax_tab(self):
        """Вкладка с синтаксическим анализатором"""
        main_frame = tk.Frame(self.syntax_frame, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        top_panel = tk.Frame(main_frame, bg='#f0f0f0')
        top_panel.pack(fill=tk.X, pady=5)
        
        start_btn = tk.Button(top_panel, text="▶ СИНТАКСИЧЕСКИЙ АНАЛИЗ", command=self.analyze_syntax,
                              bg='#F44336', fg='white', font=('Arial', 12, 'bold'),
                              relief=tk.RAISED, bd=3, width=22, height=1)
        start_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        clear_btn = tk.Button(top_panel, text="🗑 ОЧИСТИТЬ", command=self.clear_syntax_results,
                              bg='#607D8B', fg='white', font=('Arial', 10, 'bold'),
                              relief=tk.RAISED, bd=2, width=12)
        clear_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        editor_frame = tk.LabelFrame(main_frame, text="📝 Редактор (введите код Rust):", 
                                      font=("Arial", 10, "bold"), bg='#ffffff')
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.syntax_modified_label = tk.Label(editor_frame, text="", bg='#ffffff', fg='#ff0000')
        self.syntax_modified_label.pack(anchor='ne', padx=5, pady=2)
        
        self.syntax_editor = scrolledtext.ScrolledText(
            editor_frame, wrap=tk.WORD, font=("Courier New", 11),
            undo=True, background='#ffffff', foreground='#000000',
            insertbackground='#000000', selectbackground='#c0c0c0',
            padx=5, pady=5, height=10
        )
        self.syntax_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        example_syntax = """fn calc(a: i32, b: i32) -> i32 {
    return a + b
}"""
        self.syntax_editor.insert("1.0", example_syntax)
        
        # Грамматика
        grammar_frame = tk.LabelFrame(main_frame, text="📐 Грамматика", 
                                       font=("Arial", 10, "bold"), bg='#f5f5f5')
        grammar_frame.pack(fill=tk.X, padx=5, pady=5)
        
        grammar_text = """S -> fn id ( P ) -> T { return E } ;
P -> id : T | id : T , P
T -> i32 | i64 | f32 | f64 | bool
E -> id | number | ( E ) | E + E | E - E | E * E | E / E"""
        
        grammar_label = tk.Label(grammar_frame, text=grammar_text, 
                                  font=("Courier New", 10), bg='#f5f5f5', fg='#2196F3',
                                  justify=tk.LEFT)
        grammar_label.pack(anchor='w', padx=10, pady=5)
        
        # Результаты
        result_frame = tk.LabelFrame(main_frame, text="📊 Результаты синтаксического анализа:", 
                                      font=("Arial", 10, "bold"), bg='#ffffff')
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('fragment', 'position', 'message')
        self.syntax_table = ttk.Treeview(result_frame, columns=columns, show='headings', height=8)
        
        self.syntax_table.heading('fragment', text='❌ Неверный фрагмент')
        self.syntax_table.heading('position', text='📍 Местоположение')
        self.syntax_table.heading('message', text='📝 Описание ошибки')
        
        self.syntax_table.column('fragment', width=150, anchor='center')
        self.syntax_table.column('position', width=150, anchor='center')
        self.syntax_table.column('message', width=450, anchor='w')
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.syntax_table.yview)
        self.syntax_table.configure(yscrollcommand=scrollbar.set)
        
        self.syntax_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.syntax_table.bind('<ButtonRelease-1>', self.on_syntax_error_click)
        
        self.syntax_error_label = tk.Label(result_frame, text="❌ Ошибок: 0", 
                                            font=("Arial", 9, "bold"),
                                            bg='#ffffff', fg='#F44336')
        self.syntax_error_label.pack(side=tk.BOTTOM, pady=3)
    
    def setup_regex_tab(self):
        """Вкладка с поиском по регулярным выражениям"""
        main_frame = tk.Frame(self.regex_frame, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        panel_frame = tk.LabelFrame(main_frame, text="🔍 Параметры поиска", 
                                     font=("Arial", 10, "bold"), bg='#f5f5f5')
        panel_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = tk.Frame(panel_frame, bg='#f5f5f5')
        row1.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(row1, text="Выберите тип поиска:", 
                font=("Arial", 10), bg='#f5f5f5').pack(side=tk.LEFT)
        
        self.search_type = ttk.Combobox(row1, width=35, font=("Arial", 10))
        self.search_type['values'] = (
            "HEX цвет (3 символа) - #RGB",
            "Идентификатор - начинается с a-zA-Z$_",
            "Дата в формате MM/DD/YYYY"
        )
        self.search_type.current(0)
        self.search_type.pack(side=tk.LEFT, padx=10)
        
        search_btn = tk.Button(row1, text="▶ НАЙТИ", command=self.search_regex,
                              bg='#F44336', fg='white', font=('Arial', 10, 'bold'), width=12)
        search_btn.pack(side=tk.LEFT, padx=10)
        
        clear_btn = tk.Button(row1, text="🗑 ОЧИСТИТЬ", command=self.clear_regex_results,
                              bg='#607D8B', fg='white', font=('Arial', 10, 'bold'), width=12)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        row2 = tk.Frame(panel_frame, bg='#f5f5f5')
        row2.pack(fill=tk.X, padx=10, pady=5)
        
        self.pattern_label = tk.Label(row2, text="Регулярное выражение: #[0-9A-Fa-f]{3}\\b", 
                                       font=("Courier New", 10), bg='#f5f5f5', fg='#2196F3')
        self.pattern_label.pack(side=tk.LEFT)
        
        self.search_type.bind('<<ComboboxSelected>>', self.update_pattern_label)
        
        editor_frame = tk.LabelFrame(main_frame, text="📝 Редактор (введите текст):", 
                                      font=("Arial", 10, "bold"), bg='#ffffff')
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.regex_modified_label = tk.Label(editor_frame, text="", bg='#ffffff', fg='#ff0000')
        self.regex_modified_label.pack(anchor='ne', padx=5, pady=2)
        
        self.regex_editor = scrolledtext.ScrolledText(
            editor_frame, wrap=tk.WORD, font=("Courier New", 11),
            undo=True, background='#ffffff', foreground='#000000',
            insertbackground='#000000', selectbackground='#c0c0c0',
            padx=5, pady=5, height=10
        )
        self.regex_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        example_regex = """#F00 #ABC #123

Идентификаторы: $myVar _myVar myVar123 myVar

Даты: 12/31/2020 02/29/2020 01/01/2024 02/29/2021 (некорректная)"""
        self.regex_editor.insert("1.0", example_regex)
        
        result_frame = tk.LabelFrame(main_frame, text="📊 Результаты поиска:", 
                                      font=("Arial", 10, "bold"), bg='#ffffff')
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('type', 'match', 'position')
        self.regex_table = ttk.Treeview(result_frame, columns=columns, show='headings', height=8)
        
        self.regex_table.heading('type', text='🏷 Тип')
        self.regex_table.heading('match', text='📄 Найденная подстрока')
        self.regex_table.heading('position', text='📍 Позиция')
        
        self.regex_table.column('type', width=200, anchor='w')
        self.regex_table.column('match', width=300, anchor='w')
        self.regex_table.column('position', width=150, anchor='center')
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.regex_table.yview)
        self.regex_table.configure(yscrollcommand=scrollbar.set)
        
        self.regex_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.regex_table.bind('<ButtonRelease-1>', self.on_regex_click)
        
        self.regex_count_label = tk.Label(result_frame, text="🔍 Найдено: 0", 
                                          font=("Arial", 9, "bold"),
                                          bg='#ffffff', fg='#4CAF50')
        self.regex_count_label.pack(side=tk.BOTTOM, pady=3)
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="📄 Создать", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="📂 Открыть", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="💾 Сохранить", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="💾 Сохранить как", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Выход", command=self.on_closing, accelerator="Ctrl+Q")
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="↶ Отменить", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="↷ Повторить", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="✂ Вырезать", command=self.cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="📋 Копировать", command=self.copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="📝 Вставить", command=self.paste, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="🔲 Выделить все", command=self.select_all, accelerator="Ctrl+A")
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="❓ Справка", command=self.show_help, accelerator="F1")
        help_menu.add_command(label="ℹ О программе", command=self.show_about)
        
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-x>', lambda e: self.cut())
        self.root.bind('<Control-c>', lambda e: self.copy())
        self.root.bind('<Control-v>', lambda e: self.paste())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<F1>', lambda e: self.show_help())
        
    def create_toolbar(self):
        toolbar = tk.Frame(self.root, bg='#e0e0e0', height=45)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        buttons = [
            ("📄", self.new_file, "Создать", "#4CAF50"),
            ("📂", self.open_file, "Открыть", "#2196F3"),
            ("💾", self.save_file, "Сохранить", "#FF9800"),
            ("|", None, None, None),
            ("↶", self.undo, "Отменить", "#9C27B0"),
            ("↷", self.redo, "Повторить", "#9C27B0"),
            ("|", None, None, None),
            ("✂", self.cut, "Вырезать", "#E91E63"),
            ("📋", self.copy, "Копировать", "#E91E63"),
            ("📝", self.paste, "Вставить", "#E91E63"),
            ("|", None, None, None),
            ("❓", self.show_help, "Справка", "#607D8B"),
            ("ℹ", self.show_about, "О программе", "#607D8B")
        ]
        
        for icon, command, tooltip, color in buttons:
            if icon == "|":
                sep = tk.Frame(toolbar, bg='#a0a0a0', width=2, height=30)
                sep.pack(side=tk.LEFT, padx=5, pady=8)
                sep.pack_propagate(False)
            else:
                btn = tk.Button(toolbar, text=icon, command=command,
                              bg=color, fg='white',
                              font=('Segoe UI', 11, 'bold'),
                              relief=tk.RAISED, bd=2,
                              width=3, height=1)
                btn.pack(side=tk.LEFT, padx=2, pady=8)
                self.create_tooltip(btn, tooltip)
    
    def create_tooltip(self, widget, text):
        def enter(event):
            x = widget.winfo_rootx() + 25
            y = widget.winfo_rooty() + 30
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=text, background="#ffffe0", 
                           relief="solid", borderwidth=1, font=('Arial', 9))
            label.pack()
        def leave(event):
            if hasattr(self, 'tooltip') and self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
    
    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg='#e0e0e0', height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="✅ Готов", 
                                     bg='#e0e0e0', fg='#000000')
        self.status_label.pack(side=tk.RIGHT, padx=5)
    
    def update_pattern_label(self, event=None):
        patterns = {
            0: r"#[0-9A-Fa-f]{3}\b",
            1: r"[a-zA-Z$_][a-zA-Z0-9]*\b",
            2: r"(?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/(?:19|20)\d{2}"
        }
        idx = self.search_type.current()
        pattern = patterns.get(idx, r"[a-zA-Z][a-zA-Z0-9]*")
        self.pattern_label.config(text=f"Регулярное выражение: {pattern}")
    
    # ==================== ЛЕКСИЧЕСКИЙ АНАЛИЗ ====================
    def analyze_lexical(self):
        text = self.text_editor.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Предупреждение", "⚠ Введите текст для анализа")
            return
        
        self.clear_lexical_results()
        
        tokens, errors = self.lexical_analyzer.analyze(text)
        
        code_map = {
            'KEYWORD': {1: 'ключевое слово'},
            'IDENTIFIER': {2: 'идентификатор'},
            'NUMBER': {1: 'целое без знака'},
            'TYPE': {10: 'тип данных'},
            'LPAREN': {5: 'открывающая скобка'},
            'RPAREN': {6: 'закрывающая скобка'},
            'LBRACE': {7: 'открывающая фигурная'},
            'RBRACE': {8: 'закрывающая фигурная'},
            'SEMICOLON': {9: 'точка с запятой'},
            'COMMA': {4: 'запятая'},
            'COLON': {12: 'двоеточие'},
            'ASSIGN': {10: 'оператор присваивания'},
            'PLUS': {16: 'оператор сложения'},
            'MINUS': {17: 'оператор вычитания'},
            'MULTIPLY': {18: 'оператор умножения'},
            'DIVIDE': {19: 'оператор деления'},
            'ARROW': {20: 'стрелка ->'}
        }
        
        for token in tokens:
            if token['type'] in code_map:
                if token['type'] == 'KEYWORD':
                    code = 1 if token['value'] == 'fn' else 2
                    type_name = f'ключевое слово - {token["value"]}'
                elif token['type'] == 'TYPE':
                    code = 10
                    type_name = f'тип данных - {token["value"]}'
                elif token['type'] == 'NUMBER':
                    code = 1
                    type_name = 'целое без знака'
                elif token['type'] == 'IDENTIFIER':
                    code = 2
                    type_name = 'идентификатор'
                elif token['type'] == 'ARROW':
                    code = 20
                    type_name = 'стрелка (возврат)'
                else:
                    for c, tn in code_map[token['type']].items():
                        code = c
                        type_name = tn
                
                self.lexical_table.insert('', 'end', values=(
                    code, type_name, token['value'], 
                    f"строка {token['line']}, {token['start']}-{token['end']}"
                ))
        
        for error in errors:
            self.lexical_table.insert('', 'end', values=(
                99, '❌ ОШИБКА!', error['value'],
                f"строка {error['line']}, {error['start']}-{error['end']}"
            ), tags=('error',))
        
        self.lexical_table.tag_configure('error', background='#ffcccc')
        self.lexical_error_label.config(text=f"❌ Ошибок: {len(errors)}")
        
        if len(errors) == 0:
            self.status_label.config(text="✅ Лексический анализ завершен: ОШИБОК НЕТ")
        else:
            self.status_label.config(text=f"⚠ Лексический анализ: найдено {len(errors)} ошибок")
    
    def clear_lexical_results(self):
        for item in self.lexical_table.get_children():
            self.lexical_table.delete(item)
        self.lexical_error_label.config(text="❌ Ошибок: 0")
    
    # ==================== СИНТАКСИЧЕСКИЙ АНАЛИЗ ====================
    def analyze_syntax(self):
        text = self.syntax_editor.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Предупреждение", "⚠ Введите текст для анализа")
            return
        
        self.clear_syntax_results()
        
        tokens, lexical_errors = self.lexical_analyzer.analyze(text)
        
        if lexical_errors:
            for error in lexical_errors:
                self.syntax_table.insert('', 'end', values=(
                    error['value'],
                    f"строка {error['line']}, {error['start']}",
                    f"Лексическая ошибка: {error['message']}"
                ), tags=('error',))
            self.syntax_table.tag_configure('error', background='#ffcccc')
            self.syntax_error_label.config(text=f"❌ Ошибок: {len(lexical_errors)}")
            self.status_label.config(text=f"⚠ Синтаксический анализ: лексические ошибки")
            return
        
        errors = self.syntax_analyzer.parse(tokens)
        
        for error in errors:
            self.syntax_table.insert('', 'end', values=(
                error['fragment'],
                f"строка {error['line']}, {error['pos']}",
                error['message']
            ), tags=('error',))
        
        self.syntax_table.tag_configure('error', background='#ffcccc')
        self.syntax_error_label.config(text=f"❌ Ошибок: {len(errors)}")
        
        if len(errors) == 0:
            self.syntax_table.insert('', 'end', values=(
                '✅',
                '✅',
                'СИНТАКСИЧЕСКИХ ОШИБОК НЕТ'
            ), tags=('success',))
            self.syntax_table.tag_configure('success', background='#ccffcc')
            self.status_label.config(text="✅ Синтаксический анализ завершен: ОШИБОК НЕТ")
        else:
            self.status_label.config(text=f"⚠ Синтаксический анализ: найдено {len(errors)} ошибок")
    
    def on_syntax_error_click(self, event):
        item = self.syntax_table.selection()
        if not item:
            return
        
        values = self.syntax_table.item(item[0], 'values')
        if len(values) < 2:
            return
        
        position = values[1]
        try:
            import re
            match = re.search(r'строка (\d+), (\d+)', position)
            if match:
                line = int(match.group(1))
                col = int(match.group(2))
                
                self.syntax_editor.mark_set(tk.INSERT, f"{line}.{col}")
                self.syntax_editor.see(tk.INSERT)
                self.syntax_editor.focus_set()
                
                self.syntax_editor.tag_remove('highlight', '1.0', tk.END)
                self.syntax_editor.tag_configure('highlight', background='yellow', foreground='black')
                self.syntax_editor.tag_add('highlight', f"{line}.{col}", f"{line}.{col+1}")
        except:
            pass
    
    def clear_syntax_results(self):
        for item in self.syntax_table.get_children():
            self.syntax_table.delete(item)
        self.syntax_error_label.config(text="❌ Ошибок: 0")
        self.syntax_editor.tag_remove('highlight', '1.0', tk.END)
    
    # ==================== ПОИСК ПО РЕГУЛЯРНЫМ ВЫРАЖЕНИЯМ ====================
    def search_regex(self):
        text = self.regex_editor.get("1.0", tk.END)
        if not text.strip():
            messagebox.showwarning("Предупреждение", "⚠ Нет данных для поиска")
            return
        
        self.clear_regex_results()
        
        idx = self.search_type.current()
        results = []
        
        if idx == 0:
            results = self.regex_searcher.search_hex_color(text)
        elif idx == 1:
            results = self.regex_searcher.search_identifier(text)
        elif idx == 2:
            results = self.regex_searcher.search_date(text)
        
        self.current_matches = results
        
        for result in results:
            self.regex_table.insert('', 'end', values=(
                result['type'],
                result['match'],
                f"строка {result['line']}, {result['col']}"
            ))
        
        self.regex_count_label.config(text=f"🔍 Найдено: {len(results)}")
        self.status_label.config(text=f"✅ Поиск завершен: найдено {len(results)} совпадений")
    
    def on_regex_click(self, event):
        item = self.regex_table.selection()
        if not item:
            return
        
        values = self.regex_table.item(item[0], 'values')
        if len(values) < 3:
            return
        
        match_text = values[1]
        
        for match in self.current_matches:
            if match['match'] == match_text:
                self.regex_editor.tag_remove('highlight', '1.0', tk.END)
                self.regex_editor.tag_configure('highlight', background='yellow', foreground='black')
                
                start_pos = f"1.0+{match['start']}c"
                end_pos = f"1.0+{match['end']}c"
                self.regex_editor.tag_add('highlight', start_pos, end_pos)
                self.regex_editor.see(start_pos)
                break
    
    def clear_regex_results(self):
        for item in self.regex_table.get_children():
            self.regex_table.delete(item)
        self.regex_count_label.config(text="🔍 Найдено: 0")
        self.regex_editor.tag_remove('highlight', '1.0', tk.END)
    
    # ==================== ОБЩИЕ ====================
    def undo(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            try: self.text_editor.edit_undo()
            except: pass
        elif current == 1:
            try: self.syntax_editor.edit_undo()
            except: pass
        else:
            try: self.regex_editor.edit_undo()
            except: pass
    
    def redo(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            try: self.text_editor.edit_redo()
            except: pass
        elif current == 1:
            try: self.syntax_editor.edit_redo()
            except: pass
        else:
            try: self.regex_editor.edit_redo()
            except: pass
    
    def copy(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            self.text_editor.event_generate("<<Copy>>")
        elif current == 1:
            self.syntax_editor.event_generate("<<Copy>>")
        else:
            self.regex_editor.event_generate("<<Copy>>")
    
    def cut(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            self.text_editor.event_generate("<<Cut>>")
        elif current == 1:
            self.syntax_editor.event_generate("<<Cut>>")
        else:
            self.regex_editor.event_generate("<<Cut>>")
    
    def paste(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            self.text_editor.event_generate("<<Paste>>")
        elif current == 1:
            self.syntax_editor.event_generate("<<Paste>>")
        else:
            self.regex_editor.event_generate("<<Paste>>")
    
    def select_all(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            self.text_editor.tag_add(tk.SEL, "1.0", tk.END)
        elif current == 1:
            self.syntax_editor.tag_add(tk.SEL, "1.0", tk.END)
        else:
            self.regex_editor.tag_add(tk.SEL, "1.0", tk.END)
        return "break"
    
    def new_file(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            self.text_editor.delete("1.0", tk.END)
            self.clear_lexical_results()
        elif current == 1:
            self.syntax_editor.delete("1.0", tk.END)
            self.clear_syntax_results()
        else:
            self.regex_editor.delete("1.0", tk.END)
            self.clear_regex_results()
        self.text_changed = False
        self.status_label.config(text="✅ Новый файл создан")
    
    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Текстовые файлы", "*.txt"), ("Rust файлы", "*.rs"), ("Все файлы", "*.*")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    current = self.notebook.index(self.notebook.select())
                    if current == 0:
                        self.text_editor.delete("1.0", tk.END)
                        self.text_editor.insert("1.0", f.read())
                        self.clear_lexical_results()
                    elif current == 1:
                        self.syntax_editor.delete("1.0", tk.END)
                        self.syntax_editor.insert("1.0", f.read())
                        self.clear_syntax_results()
                    else:
                        self.regex_editor.delete("1.0", tk.END)
                        self.regex_editor.insert("1.0", f.read())
                        self.clear_regex_results()
                self.status_label.config(text=f"✅ Открыт файл: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"❌ Не удалось открыть файл:\n{str(e)}")
    
    def save_file(self):
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                               filetypes=[("Текстовые файлы", "*.txt"), ("Rust файлы", "*.rs"), ("Все файлы", "*.*")])
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.text_editor.get("1.0", tk.END))
                self.status_label.config(text=f"✅ Сохранено: {os.path.basename(path)}")
        elif current == 1:
            path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                               filetypes=[("Текстовые файлы", "*.txt"), ("Rust файлы", "*.rs"), ("Все файлы", "*.*")])
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.syntax_editor.get("1.0", tk.END))
                self.status_label.config(text=f"✅ Сохранено: {os.path.basename(path)}")
        else:
            path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                               filetypes=[("Текстовые файлы", "*.txt"), ("Rust файлы", "*.rs"), ("Все файлы", "*.*")])
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.regex_editor.get("1.0", tk.END))
                self.status_label.config(text=f"✅ Сохранено: {os.path.basename(path)}")
    
    def save_as_file(self):
        self.save_file()
    
    def show_help(self):
        messagebox.showinfo("Справка", 
            "📚 СПРАВКА\n\n"
            "📌 Лексический анализатор (вкладка 1):\n"
            "   - Введите код Rust\n"
            "   - Нажмите 'ЛЕКСИЧЕСКИЙ АНАЛИЗ'\n"
            "   - Результаты в таблице\n\n"
            "🔧 Синтаксический анализатор (вкладка 2):\n"
            "   - Введите код Rust\n"
            "   - Нажмите 'СИНТАКСИЧЕСКИЙ АНАЛИЗ'\n"
            "   - Результаты (ошибки) в таблице\n\n"
            "📐 Грамматика:\n"
            "   S -> fn id ( P ) -> T { return E } ;\n"
            "   P -> id : T | id : T , P\n"
            "   T -> i32 | i64 | f32 | f64 | bool\n"
            "   E -> id | number | ( E ) | E + E | E - E | E * E | E / E\n\n"
            "🔍 Поиск по регулярным выражениям (вкладка 3):\n"
            "   - HEX цвет: #RGB\n"
            "   - Идентификатор: буква, $ или _, затем буквы/цифры\n"
            "   - Дата: MM/DD/YYYY (с проверкой високосных)\n\n"
            "🖱 Кликните на ошибку для перехода к ней в редакторе")
    
    def show_about(self):
        messagebox.showinfo("О программе", 
            "🦀 Языковой процессор\n"
            "Вариант 75: Rust\n\n"
            "📝 Лексический анализатор (ЛР №2)\n"
            "🔧 Синтаксический анализатор (ЛР №3)\n"
            "   - Метод Айронса (нейтрализация ошибок)\n"
            "🔍 Поиск по регулярным выражениям (ЛР №4)\n\n"
            "© 2026")


def main():
    root = tk.Tk()
    app = TextEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
