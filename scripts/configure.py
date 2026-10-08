"""Source-kit convenience wrapper for the installed private profile generator."""

from crous_queue.configuration import configure

if __name__ == "__main__":
    configure()
    print("Development .env ready; existing secrets preserved.")
