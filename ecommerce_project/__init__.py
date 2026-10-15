"""Project package. Registers PyMySQL as the MariaDB/MySQL driver when it is installed."""
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # SQLite fallback needs no driver
    pass
