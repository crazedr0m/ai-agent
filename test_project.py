# test_project.py
import project_code

def test_addition():
    assert project_code.add_numbers(2, 3) == 5, "Ошибка: 2 + 3 должно быть равно 5!"

if __name__ == "__main__":
    test_addition()
    print("SUCCESS")
