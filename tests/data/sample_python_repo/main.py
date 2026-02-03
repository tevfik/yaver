def hello():
    print("Hello DevMind Analysis!")

class DemoProcessor:
    def __init__(self, name):
        self.name = name
    
    def process(self, data):
        return f"Processed {data} by {self.name}"

if __name__ == "__main__":
    hello()
    p = DemoProcessor("Tester")
    p.process("Input")
