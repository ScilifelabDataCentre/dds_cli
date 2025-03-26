from dds_cli.gui_poc.app import DDSApp

if __name__ == "__main__":
    app = DDSApp(token_path="~/.dds_cli_token")
    app.run()
