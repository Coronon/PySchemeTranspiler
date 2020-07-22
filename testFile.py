def a(a: int) -> int:
    return a + 17

def b(b: int) -> float:
    return a(b) + 3.14

print(b(a(7)))
print()