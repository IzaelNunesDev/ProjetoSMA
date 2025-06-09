import fastmcp
import inspect

print("--- Contents of fastmcp module ---")
print(dir(fastmcp))
print("\n--- Attempting to locate MCPHub ---")

found_mcphub = False
for name, obj in inspect.getmembers(fastmcp):
    if name == 'MCPHub':
        print(f"Found MCPHub directly: {obj}")
        found_mcphub = True
        break
    if inspect.ismodule(obj):
        print(f"Checking submodule: fastmcp.{name}")
        try:
            if 'MCPHub' in dir(obj):
                print(f"Found MCPHub in submodule fastmcp.{name}")
                # Attempt to import to confirm
                exec(f"from fastmcp.{name} import MCPHub")
                print(f"Successfully imported MCPHub from fastmcp.{name}")
                found_mcphub = True
                break
        except Exception as e:
            print(f"Could not inspect or import from fastmcp.{name}: {e}")

if not found_mcphub:
    print("\nMCPHub not found directly or in common submodules of fastmcp.")

print("\n--- Checking __init__.py path ---")
print(fastmcp.__file__)
