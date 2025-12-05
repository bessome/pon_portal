from app import create_app

app = create_app()

if __name__ == "__main__":
    # use_reloader disabled to avoid double scheduler start
    app.run(debug=True, use_reloader=False)
