import kivy
from kivy.app import App
from kivy.uix.label import Label


# Define the main application class
class HelloWorldApp(App):
    def build(self):
        # Return a label widget with the text "Hello, World!"
        return Label(text='Hello, World!', font_size=36)


# Run the app
if __name__ == '__main__':
    HelloWorldApp().run()
