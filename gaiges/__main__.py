"""Allow running as: python -m gaiges"""
from gaiges.cluster import choose_skin, TokenDashboard

def main():
    skin = choose_skin()
    TokenDashboard(skin)

if __name__ == "__main__":
    main()
