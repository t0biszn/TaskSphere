import sqlite3
from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.config import Config
from kivy.properties import Property, StringProperty, ListProperty, DictProperty
from kivy.utils import get_color_from_hex
import hashlib
from datetime import datetime, timedelta
from plyer import notification

Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

def get_today_date():
    return datetime.today().strftime("%d-%m-%Y")

def get_future_date(days):
    return (datetime.today() + timedelta(days=days)).strftime("%d-%m-%Y")

def check_due_tasks(user_id):
    today = get_today_date()
    tomorrow = get_future_date(1)
    three_days = get_future_date(3)

    conn = sqlite3.connect("task_manager.db")
    cur = conn.cursor()
    cur.execute("SELECT title, due_date FROM tasks WHERE user_id = ? AND due_date IN (?, ?, ?) AND status = 'pending'",
                (user_id, today, tomorrow, three_days))
    tasks = cur.fetchall()
    conn.close()

    if tasks:
        for title, due_date in tasks:
            due_date_obj = datetime.strptime(due_date, "%d-%m-%Y").date()
            today_obj = datetime.strptime(today, "%d-%m-%Y").date()
            # converts dates to objects so that any problems with time (as in a few hours difference)
            days_left = (due_date_obj - today_obj).days

            if days_left == 0:
                message = f"'{title}' is due today."
            elif days_left == 1:
                message = f"'{title}' is due tomorrow."
            else:
                message = f"'{title}' is due in 3 days."

            notification.notify(
                title="Task Reminder",
                message=message,
                app_name="TaskSphere"
            )
        print(f"Notification sent: {message}")
    else:
        print("No due tasks found.")
    return

class Theme(Widget):
    colors = DictProperty({  # Creates dictionary to hold theme colours
        "background": get_color_from_hex("#FFFFFF"),  # White
        "text": get_color_from_hex("#000000"),  # Black for normal text
        "button": get_color_from_hex("#757575"),  # Dark grey for button colour
        "button_text": get_color_from_hex("#FFFFFF"),  # White for button text
        "outline": get_color_from_hex("#000000"),  # Black for outlines
        "logout": get_color_from_hex("#ffb0b0"),  # Red for logout
        "delete": get_color_from_hex("#ffb0b0"),  # Red for delete
        "edit": get_color_from_hex("#abd4ff"),
        "delete_text": get_color_from_hex("#D32F2F"),
        "logout_text": get_color_from_hex("#D32F2F"),
        "edit_text": get_color_from_hex("#1976D2")  # Blue for edit
    })


initcon = sqlite3.connect("task_manager.db")
initcur = initcon.cursor()
initcur.execute("""
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    logged_in INTEGER DEFAULT 0
    )
""")

initcur.execute("""
CREATE TABLE IF NOT EXISTS Categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_name TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users (user_id)
)    
""")

initcur.execute("""
CREATE TABLE IF NOT EXISTS Tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    priority INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES Users (user_id),
    FOREIGN KEY (category_id) REFERENCES Categories (category_id)
)
""")

initcon.commit()
initcon.close()


class sm(ScreenManager):  # defines sm class which inherits from ScreenManager, which manages screens in the app
    pass


class BaseScreen(Screen):
    pass


class ChooseScreen(BaseScreen):
    pass


class LoginScreen(BaseScreen):
    def on_pre_enter(self):
        f_label = self.ids.feedback_label
        f_label.text = ""
        usnm_input = self.ids.username_input
        usnm_input.text = ""
        pass_input = self.ids.password_input
        pass_input.text = ""

    def login_form(self, login_username, login_password):
        login_feedback_message = self.ids.feedback_label  # this creates an instance of the feedback label that is
        # created in my kv file
        if self.password_validation(login_username, login_password):
            conn = sqlite3.connect("task_manager.db")
            cur = conn.cursor()
            cur.execute("UPDATE Users SET logged_in = 0")  # this makes sure that all other users that might be logged
            # in are logged out to prevent more than one user from being logged in
            cur.execute("UPDATE Users SET logged_in = 1 WHERE username = ?", (login_username,))
            # this sets the user that has been logged in to have a logged_in value of 1
            conn.commit()
            login_feedback_message.text = "Login successful!"  # outputs confirmation message
            login_feedback_message.color = (0, 1, 0, 1)
            self.manager.current = "main"  # changes screen to main screen
            return True
        else:
            login_feedback_message.text = "Invalid username or password"  # outputs error message
            login_feedback_message.color = (1, 0, 0, 1)
            return False

    def password_validation(self, login_username, login_password):  # function to check the login details against the
        # Users table
        conn = None
        try:  # tries to connect to the database use the username parameter to find a password that matches
            conn = sqlite3.connect("task_manager.db")
            cur = conn.cursor()
            cur.execute("SELECT password_hash FROM Users WHERE username = ?", (login_username,))
            result = cur.fetchone()  # stores the password that has been fetched

            if result:
                stored_password_hash = result[0]
                input_password_hash = hashlib.sha256(login_password.encode()).hexdigest()
                return stored_password_hash == input_password_hash  # returns True if the hash of the inputted
                # password matches the stored hash related to the username
            else:
                return False  # otherwise returns false
        except sqlite3.Error:  # returns false if there is a database error (indicating username is not in the table)
            return False
        finally:  # closes the database connection regardless of the result
            if conn:
                conn.close()


class SignupScreen(BaseScreen):
    def on_pre_enter(self):
        f_label = self.ids.feedback_label
        f_label.text = ""
        usnm_input = self.ids.username_input
        usnm_input.text = ""
        pass_input = self.ids.password_input
        pass_input.text = ""
        # Sets inputs and feedback label to be blank

    def username_validation(self, signup_username):
        if len(signup_username) < 4:
            return False, "Username must be 4+ characters."  # If the username is less than 4 characters long,
            # the validation fails and the method returns both False and a message.

        uval_conn = sqlite3.connect("task_manager.db")
        uval_cur = uval_conn.cursor()
        uval_cur.execute("SELECT username FROM Users WHERE username = ?", (signup_username,))
        dup_username = uval_cur.fetchone()
        # this code checks if there is a username that is equal, and if so stores this value as a variable so the
        # connection can be closed.
        uval_conn.commit()
        uval_conn.close()

        if dup_username:
            return False, "Username taken."  # if fetchone() returns a result, the username is taken.
        return True, None  # If the username passes validation, the function returns True.

    def password_validation(self, signup_password):
        special_characters = "!£$%^&*()@"  # Defines the set of special characters that must be present in the password

        if len(signup_password) < 8:
            return False, "Password must be at least 8 characters long."
            # Returns false if password is too short
        if not any(char.isupper() for char in signup_password):
            return False, "Password must contain at least one uppercase letter."
            # returns false if password does not contain an uppercase character
        if not any(char.isdigit() for char in signup_password):
            return False, "Password must contain at least one digit."
            # Returns false if password does not contain a numerical digit
        if not any(char in special_characters for char in signup_password):
            return False, "Password must contain at least one special character."
            # Returns false if password does not contain a special character

        return True, None

    def populate_users(self, username, password_hash):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO Users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        # signs user up
        user_id = self.get_userid(username)
        cur.execute("INSERT INTO Categories (category_name, user_id) VALUES ('None', ?)", (user_id,))
        # adds "None" to the Categories table
        conn.commit()
        conn.close()

    def signup_validation(self, signup_username, signup_password):
        signup_feedback_label = self.ids.feedback_label  # Creates an instance of the feedback_label ID from my .kv file
        usnm_valid, usnm_message = self.username_validation(signup_username)
        # Passes values into username_validation() to get the return values
        pass_valid, message = self.password_validation(signup_password)
        # Passes values into password_validation() to get the return values
        password_hash = hashlib.sha256(signup_password.encode()).hexdigest()
        # Hashes the inputted password
        if not usnm_valid:
            signup_feedback_label.text = usnm_message
            signup_feedback_label.color = (1, 0, 0, 1)
            return
            # Displays error message if username validation failed
        elif not pass_valid:
            signup_feedback_label.text = message
            signup_feedback_label.color = (1, 0, 0, 1)
            return
            # Displays error message if password validation failed
        else:
            self.populate_users(signup_username, password_hash)
            # Populates the database with values if they are valid
            self.manager.current = "login"
            # Changes to current screen to the login screen if the signup was successful

    def get_userid(self, username):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        result = cur.fetchone()
        user_id = result[0]
        return user_id


class MainScreen(BaseScreen):
    def log_out(self, ):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("UPDATE Users SET logged_in = 0")  # Logs out any logged in users when the method is called
        conn.commit()
        conn.close()
        self.manager.current = "choosescreen"  # Changes current screen to the ChooseScreen


class CreateTask(BaseScreen):
    categories = ListProperty([])

    def on_pre_enter(self):
        self.ids.title_input.text = ""
        self.ids.due_date_input.text = ""
        self.ids.description_input.text = ""
        self.ids.feedback_label.text = ""
        # Sets all text input fields to be empty

        self.ids.low_priority.active = False
        self.ids.medium_priority.active = False
        self.ids.high_priority.active = False
        # Ensures that no priority is selected

        self.ids.category_spinner.text = "Select Category"
        # Ensures that no category is selected

        self.get_categories()

    def created_task_validation(self, inp_title, inp_date, inp_descr, inp_category, inp_priority):
        if not inp_title.strip():
            return False, "Title cannot be empty"

        if len(inp_title) > 30:
            return False, "Title must be less than 30 characters."

        if len(inp_descr) > 200:
            return False, "Description must be less than 200 characters."

        try:
            datetime.strptime(inp_date, "%d-%m-%Y")
        except ValueError:
            return False, "Due date must be in format DD-MM-YYYY."

        if inp_category == "Select Category":
            return False, "Please select a category."

        if inp_priority is None:
            return False, "Please select a priority."

        return True, None

    def get_logged_in(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE logged_in = 1 LIMIT 1")  # Gets user_ID of a user that is logged in
        result = cur.fetchone()
        user_id = result[0]  # the actual integer is now returned
        return user_id

    def get_category_id(self, category_name, user_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM categories WHERE category_name = ? AND user_id = ?",
                    (category_name, user_id))
        result = cur.fetchone()
        category_id = result[0]
        return category_id

    def get_priority(self):
        if self.ids.low_priority.active:
            return 1
        elif self.ids.medium_priority.active:
            return 2
        elif self.ids.high_priority.active:
            return 3

    def insert_task(self, inp_title, inp_date, inp_descr, inp_priority, category_id, user_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("""
                INSERT INTO Tasks (user_id, category_id, title, description, due_date, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, category_id, inp_title, inp_descr, inp_date, inp_priority, "pending"))
        conn.commit()
        conn.close()

    def convert_priority(self):
        if self.get_priority() == 1:
            return "Low"
        elif self.get_priority() == 2:
            return "Medium"
        else:
            return "High"

    def create_task(self):
        inp_title = self.ids.title_input.text
        inp_date = self.ids.due_date_input.text
        inp_descr = self.ids.description_input.text
        inp_category = self.ids.category_spinner.text
        inp_priority = self.get_priority()
        feedback_label = self.ids.feedback_label

        print(inp_category)
        # all input values are stored as local variables

        valid, error_message = self.created_task_validation(inp_title, inp_date, inp_descr, inp_category, inp_priority)
        if not valid:
            feedback_label.text = error_message
            feedback_label.color = (1, 0, 0, 1)
            return
        # Input values are validated, and if they are not valid, the relevant message is displayed

        user_id = self.get_logged_in()
        # user_id is found by checking which user is logged in
        category_id = self.get_category_id(inp_category, user_id)
        # category_id is found by using the inputted category's name and user_id

        self.insert_task(inp_title, inp_date, inp_descr, inp_priority, category_id, user_id)
        # task is inserted into database

        view_task_screen = self.manager.get_screen("view_task")
        view_task_screen.task_title = self.ids.title_input.text
        view_task_screen.task_due_date = self.ids.due_date_input.text
        view_task_screen.task_description = self.ids.description_input.text
        view_task_screen.task_priority = self.convert_priority()
        view_task_screen.task_status = "Pending"
        view_task_screen.task_category_id = str(category_id)
        view_task_screen.task_id = str(self.get_task_id(inp_title, inp_date))
        # Sets all the View Task screen's properties to be the details that have just been inputted
        self.manager.current = "view_task"
        # Changes the current screen to be the View Task screen


    def get_categories(self):
        user_id = self.get_logged_in()
        # finds the logged in user
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_name FROM Categories WHERE user_id = ?", (user_id,))
        conn.commit()
        user_categories = cur.fetchall()
        # stores all categories in this user_categories variable
        conn.close()
        self.categories = [cat[0] for cat in user_categories]
        # adds every category in user_categories to the categories list property

    def get_task_id(self, title, due_date):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT task_id FROM tasks WHERE title = ? AND due_date = ?", (title, due_date))
        result = cur.fetchone()
        task_id = result[0]
        conn.close()
        return task_id


class NavigationMenu(BaseScreen):
    def on_enter(self):
        self.load_category_buttons()
        # Method is called when the screen opens

    def load_category_buttons(self):
        self.ids.category_layout.clear_widgets()  # Removes all existing widgets from the layout
        user_id = self.get_logged_in()  # Stores the logged in user_id

        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_name FROM Categories WHERE user_id = ?", (user_id,))
        categories = cur.fetchall()
        conn.close()
        # Fetches all categories from the Categories table based on the user that is logged in

        for category in categories:
            category_name = category[0]
            btn = Button(
                text=category_name,
                size_hint_y=None,
                height=40,
                on_press=lambda btn, cat_name=category_name: self.filter_tasks("category", cat_name)
            )
            self.ids.category_layout.add_widget(btn)
        # Every category that has been fetched is created as a button on screen

    def get_logged_in(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE logged_in = 1 LIMIT 1")  # Gets user_ID of a user that is logged in
        result = cur.fetchone()
        user_id = result[0]
        return user_id

    def filter_tasks(self, filter_type, category=None):
        task_list_screen = self.manager.get_screen('task_list_screen')
        task_list_screen.filter_type = filter_type
        task_list_screen.selected_category = category
        self.manager.current = 'task_list_screen'
        # Passes the filter into the task list screen so that correct tasks are displayed

    def log_out(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute(
            "UPDATE Users SET logged_in = 0")  # Logs out any logged in users when the method is called
        cur.execute("SELECT * FROM Users")
        conn.commit()
        conn.close()
        self.manager.current = "choosescreen"  # Changes current screen to the ChooseScreen


class TaskListScreen(BaseScreen):
    filter_type = StringProperty("all")  # This specifies what type of filter is being used, status (today,
    # completed, all) or category. and is set to all by default
    selected_category = StringProperty(None)  # This specifies the category that has been chosen, and is None for
    # status filters.

    def on_enter(self):
        logged_in = self.get_logged_in()
        # finds the user that is logged in
        filter_type = self.filter_type
        # calls the filter_type property to a local variable
        category = self.selected_category
        # calls the selected_category property to a local variable

        user_id = self.get_logged_in()

        query = "SELECT task_id, title, description, due_date, priority, status, category_id FROM Tasks"
        # I have added the task_id to the Table search
        params = []
        # Creates the basic query that will be used to select tasks, and also creates an array to store any parameters

        # I have changed all of my queries to contain a clause that orders tasks by priority descending
        if filter_type == "category" and category:
            category_id = self.get_category_id(self.selected_category, logged_in)
            # finds the category id of the selected_category property, storing that to a local variable as well
            query += " WHERE category_id = ? AND user_id = ? AND status = 'pending' ORDER BY priority DESC"
            params.append(category_id)
            params.append(user_id)
        # Edits the query to search for tasks with a specific category, adds the category to the parameters array

        elif filter_type == "today":
            query += " WHERE due_date = ? AND user_id = ? AND status = 'pending' ORDER BY priority DESC"
            params.append(self.get_today_date())
            params.append(user_id)
        # Edits the query to search for tasks that have a specific due date, making the parameter today's date

        elif filter_type == "completed":
            query += " WHERE status = ? AND user_id = ? ORDER BY priority DESC"
            params.append("completed")
            params.append(user_id)
        # Edits the query to search for tasks with a specific status, making the parameter "completed"

        elif filter_type == "all":
            query += " WHERE user_id = ? AND status = 'pending' ORDER BY priority DESC"
            params.append(user_id)
        # No filtering, this just displays all tasks
        # every query now has user_id as a parameter as well as whatever the old parameter was.

        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        tasks = cur.fetchall()
        conn.close()

        task_list_layout = self.ids.task_list_layout
        task_list_layout.clear_widgets()
        # removes any widgets that might already be present

        for task in tasks:
            task_id, title, description, due_date, priority, status, category_id = task
            task_button = Button(
                text=f"{title}\nDue: {due_date} Priority: {self.get_priority_text(priority)}",
                # \n makes sure there is a break after the title, so that the due date and priority are on a new line.
                size_hint_y=None,
                text_size=(self.width, None),
                halign='left',
                padding=[30, 10],
                height=50,
                on_press=lambda task_button, t=task: self.on_task_pressed(t[0], t[1], t[2], t[3], t[4], t[5], t[6])
                # I have also passed the task_id into the on_task_pressed() method
            )
            task_list_layout.add_widget(task_button)
        # Adds each task to the task_list_layout, with their title, due date, priority and status

    def get_today_date(self):
        return datetime.today().strftime('%d-%m-%Y')

    def get_category_id(self, category_name, user_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM categories WHERE category_name = ? AND user_id = ?",
                    (category_name, user_id))
        result = cur.fetchone()
        category_id = result[0]
        return category_id

    def get_logged_in(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE logged_in = 1 LIMIT 1")  # Gets user_ID of a user that is logged in
        result = cur.fetchone()
        user_id = result[0]
        return user_id

    def on_task_pressed(self, task_id, title, description, due_date, priority, status, category_id):
        view_task_screen = self.manager.get_screen("view_task")
        view_task_screen.task_title = title
        view_task_screen.task_description = description
        view_task_screen.task_due_date = due_date
        view_task_screen.task_priority = self.get_priority_text(priority)
        # sets the task_priority property to be the string that is fetched when the get_priority_text method is called.
        view_task_screen.task_status = status
        view_task_screen.task_category_id = str(category_id)
        view_task_screen.task_id = str(task_id)
        # I have added task_id to the on_task_pressed() method, making sure that the view_task_pressed property (task_id) is updated

        self.manager.current = "view_task"

    def get_priority_text(self, priority):
        if priority == 1:
            return "Low"
        elif priority == 2:
            return "Medium"
        elif priority == 3:
            return "High"


class ViewTask(BaseScreen):
    task_title = StringProperty("")
    task_description = StringProperty("")
    task_due_date = StringProperty("")
    task_priority = StringProperty("")
    task_status = StringProperty("")
    task_category_id = StringProperty("")
    task_category_name = StringProperty("")
    task_id = StringProperty("")
    # Here I created the task_id as a property in the View Task screen

    def on_enter(self):
        cat_name = self.get_cat_name(self.task_category_id)
        self.task_category_name = cat_name

    def mark_completed(self, task_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("UPDATE Tasks SET status = 'completed' WHERE task_id = ? ", (int(task_id),))
        # This query now uses task_id instead of title
        conn.commit()
        conn.close()
        # Changes the status of the current task to "completed".

        self.manager.current = "nav_menu"

    def delete_task(self, task_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM Tasks WHERE task_id = ?", (int(task_id),))
        # This query now uses task_id instead of title
        conn.commit()
        conn.close()
        # Deletes the task from the table

        self.manager.current = "nav_menu"

    def get_cat_name(self, cat_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_name FROM Categories WHERE category_id = ?", ((int(cat_id)),))
        # Query to find the category name that matches the ID that is passed in
        result = cur.fetchone()
        cat_name = result[0]
        conn.commit()
        conn.close()
        return cat_name


class EditTaskScreen(BaseScreen):
    categories = ListProperty([])
    task_title = StringProperty("")
    task_description = StringProperty("")
    task_due_date = StringProperty("")
    task_priority = StringProperty("")
    task_category = StringProperty("")
    task_id = StringProperty("")
    # I have added task_id as a property in the Edit Task screen

    def on_enter(self):
        self.get_categories()

    def retrieve_details(self, task_id, title, due_date, description, priority):
        self.task_id = task_id
        # task_id property is changed to be the correct task_id
        self.task_title = title
        self.task_description = description
        self.task_due_date = due_date
        self.task_priority = priority
        self.task_category = self.get_category(self.task_id)

    # Sets properties to be the values passed in

    def get_category(self, task_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM Tasks WHERE task_id = ?", (task_id,))
        # This query now uses task_id instead of title
        result = cur.fetchone()
        cat_id = result[0]
        # Finds the category_id of the task
        cur.execute("SELECT category_name FROM Categories WHERE category_id = ?", (cat_id,))
        result2 = cur.fetchone()
        cat_name = result2[0]
        # finds the category name that matches the category ID and returns it
        return cat_name

    def edit_task_validation(self, inp_title, inp_date, inp_descr, inp_category, inp_priority):
        if not inp_title.strip():
            return False, "Title cannot be empty"

        if len(inp_title) > 30:
            return False, "Title must be less than 30 characters."

        if len(inp_descr) > 200:
            return False, "Description must be less than 200 characters."

        try:
            datetime.strptime(inp_date, "%d-%m-%Y")
        except ValueError:
            return False, "Due date must be in format DD-MM-YYYY."

        if inp_category == "Select Category":
            return False, "Please select a category."

        if inp_priority is None:
            return False, "Please select a priority."

        return True, None

    def get_logged_in(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE logged_in = 1 LIMIT 1")  # Gets user_ID of a user that is logged in
        result = cur.fetchone()
        user_id = result[0]  # the actual integer is now returned
        return user_id

    def get_category_id(self, category_name, user_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM categories WHERE category_name = ? AND user_id = ?",
                    (category_name, user_id))
        result = cur.fetchone()
        category_id = result[0]
        return category_id

    def get_priority(self):
        if self.ids.low_priority.active:
            return 1
        elif self.ids.medium_priority.active:
            return 2
        elif self.ids.high_priority.active:
            return 3

    def convert_priority(self):
        if self.get_priority() == 1:
            return "Low"
        elif self.get_priority() == 2:
            return "Medium"
        elif self.get_priority() == 3:
            return "High"

    def update_task(self, new_title, due_date, description, priority, category_id, user_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("UPDATE Tasks SET title = ?, due_date = ?, description = ?, priority = ?, category_id = ? WHERE "
                    "task_id = ? AND user_id = ?", (new_title, due_date, description, priority, category_id,
                                                  self.task_id, user_id))
        # This query now uses task_id instead of title
        conn.commit()  # This commits the changes to the database to make sure they actually happen
        conn.close()

    def edit_task(self):
        inp_title = self.ids.title_input.text
        inp_date = self.ids.due_date_input.text
        inp_descr = self.ids.description_input.text
        inp_category = self.ids.category_spinner.text
        inp_priority = self.get_priority()
        feedback_label = self.ids.feedback_label

        print(inp_category)
        # all input values are stored as local variables

        valid, error_message = self.edit_task_validation(inp_title, inp_date, inp_descr, inp_category, inp_priority)
        if not valid:
            feedback_label.text = error_message
            feedback_label.color = (1, 0, 0, 1)
            return
        # Input values are validated, and if they are not valid, the relevant message is displayed

        user_id = self.get_logged_in()
        # user_id is found by checking which user is logged in
        category_id = self.get_category_id(inp_category, user_id)
        # category_id is found by using the inputted category's name and user_id

        self.update_task(inp_title, inp_date, inp_descr, inp_priority, category_id, user_id)
        # task is inserted into database

        view_task_screen = self.manager.get_screen("view_task")
        view_task_screen.task_title = inp_title
        view_task_screen.task_due_date = inp_date
        view_task_screen.task_description = inp_descr
        view_task_screen.task_priority = self.convert_priority()
        view_task_screen.task_category_id = str(category_id)
        view_task_screen.task_id = self.task_id
        # All of the view task screen's properties are changed to match the inputted properties

        self.manager.current = "view_task"
        # Current screen is changed to View Task screen


    def get_categories(self):
        user_id = self.get_logged_in()
        # finds the logged in user
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT category_name FROM Categories WHERE user_id = ?", (user_id,))
        conn.commit()
        user_categories = cur.fetchall()
        # stores all categories in this user_categories variable
        conn.close()
        self.categories = [cat[0] for cat in user_categories]
        # adds every category in user_categories to the categories list property


class CreateCategory(BaseScreen):
    def on_pre_enter(self):
        cat_field = self.ids.category_name_input
        cat_field.text = ""
        f_label = self.ids.feedback_label
        f_label.text = ""

    def create_category(self, category_name):
        user_id = self.get_logged_in()
        # gets logged in user
        feedback_label = self.ids.feedback_label
        # makes sure the feedback label can be changed within this message by turning it into a variable
        valid, message = self.category_validation(category_name)
        # calls the category_validation() method to determine whether the category name is valid or not
        if valid:
            self.add_cat_to_table(category_name, user_id)
            self.manager.current = "main"
            # if the category name is valid, the category is added to the table and the user is returned to the main
            # screen
        else:
            feedback_label.text = message
            feedback_label.color = (1, 0, 0, 1)
            # if the category name is not valid, the relevant message is displayed

    def get_logged_in(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM Users WHERE logged_in = 1 LIMIT 1")  # Gets user_ID of a user that is logged in
        result = cur.fetchone()
        user_id = result[0]  # the actual integer is now returned
        return user_id

    def category_validation(self, category_name):
        if not category_name.strip():
            return False, "Category name cannot be empty"
            # checks if name is present
        elif len(category_name) > 20:
            return False, "Category name must be less than 20 characters"
            # checks if name is too long
        else:
            return True, None
            # returns true if the category name is valid

    def add_cat_to_table(self, category_name, user_id):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO Categories (category_name, user_id) VALUES (?, ?)", (category_name, user_id))
        conn.commit()
        conn.close()
        # adds the category to the database


class MyApp(App):  # defines the main application class which inherits from App
    theme = Theme()

    def build(self):
        sm_instance = sm(transition=NoTransition())  # creates an instance of the sm class
        sm_instance.add_widget(MainScreen(name="main"))  # adds the MainScreen screen to the screen manager
        sm_instance.add_widget(ChooseScreen(name="choosescreen"))  # adds the ChooseScreen screen to the screen manager
        sm_instance.add_widget(LoginScreen(name="login"))  # adds the LoginScreen screen to the screen manager
        sm_instance.add_widget(SignupScreen(name="signup"))  # adds the SignupScreen screen to the screen manager
        sm_instance.add_widget(CreateTask(name="createtask"))  # adds the CreateScreen screen to the screen manager
        sm_instance.add_widget(NavigationMenu(name="nav_menu"))  # Adds the menu to the screen manager
        sm_instance.add_widget(TaskListScreen(name="task_list_screen"))
        sm_instance.add_widget(ViewTask(name="view_task"))
        sm_instance.add_widget(EditTaskScreen(name="edit_task"))
        sm_instance.add_widget(CreateCategory(name="create_category"))

        logged_in_user = self.get_logged_in_user()  # calls the method that finds a logged in user
        if logged_in_user:
            check_due_tasks(logged_in_user)
            sm_instance.current = "main"  # opens MainScreen straight away

        else:
            sm_instance.current = "choosescreen"  # opens ChooseScreen straight away
        return sm_instance

    def get_logged_in_user(self):
        conn = sqlite3.connect("task_manager.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE logged_in = 1 LIMIT 1")  # selects a user who is logged in
        result = cur.fetchone()
        conn.close()
        if result:
            return result[0]  # Return username of logged in user
        return None  # Returns nothing if there is no logged in user


MyApp().run()  # starts the application
