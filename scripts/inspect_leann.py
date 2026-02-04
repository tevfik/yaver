import leann
import inspect

def print_class_info(cls):
    print(f"Class: {cls.__name__}")
    print(f"Doc: {cls.__doc__}")
    for name, method in inspect.getmembers(cls):
        if not name.startswith('_'):
            print(f"  Method: {name}")
            try:
                print(f"    Sig: {inspect.signature(method)}")
            except:
                pass

print("=== LeannBuilder ===")
print_class_info(leann.LeannBuilder)

print("\n=== LeannSearcher ===")
print_class_info(leann.LeannSearcher)
