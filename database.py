import psycopg2


class Tables:
    """Обобщение обычных функций в postgresql"""

    def __init__(self, token: int):
        # соединение с сервером с помощью url
        self.connection = psycopg2.connect(token)

    async def insert(self, table_name: str, **kwargs):

        names = []
        values = []

        for key, value in kwargs.items():
            names.append(key)
            values.append(f"\'{value}\'")

        name_string = ', '.join(names)
        value_string = ', '.join(values)

        await self.execute(f"INSERT INTO {table_name} ({name_string}) VALUES ({value_string})")

    async def delete(self, table_name: str, **kwargs):

        condition = []

        for key, value in kwargs.items():
            condition.append(f"{key} = \'{value}\'")

        full_condition = ' AND '.join(condition)

        await self.execute(f"DELETE FROM {table_name} WHERE {full_condition}")

    async def get_column_names(self, table_name: str):

        rows = await self.select(f"SELECT column_name FROM information_schema.columns where table_name = \'{table_name}\'")

        res = []
        for row in rows:
            res.append(row[0])

        return res

    async def fetch(self, table_name: str, **kwargs):

        column_names = await self.get_column_names(table_name)
        condition = []

        for key, value in kwargs.items():
            condition.append(f"{key} = \'{value}\'")

        full_condition = ' AND '.join(condition)

        res = []
        if full_condition:
            command = f"SELECT * FROM {table_name} WHERE {full_condition}"
        else:
            command = f"SELECT * FROM {table_name}"

        for row in await self.select(command):
            res_row = dict()

            for index in range(len(row)):
                column_name = column_names[index]
                value = row[index]
                res_row[column_name] = value

            res.append(res_row)

        return res

    async def fetchrow(self, table_name: str, **kwargs):

        column_names = await self.get_column_names(table_name)
        condition = []

        for key, value in kwargs.items():
            condition.append(f"{key} = \'{value}\'")

        full_condition = ' AND '.join(condition)
        res = dict()

        if full_condition:
            command = f"SELECT * FROM {table_name} WHERE {full_condition} FETCH FIRST ROW ONLY"
        else:
            command = f"SELECT * FROM {table_name} FETCH FIRST ROW ONLY"

        something = await self.select(command)

        if len(something) == 0:
            return None

        row = something[0]

        for index in range(len(row)):
            column_name = column_names[index]
            value = row[index]
            res[column_name] = value

        return res

    async def execute(self, command: str):

        with self.connection.cursor() as cursor:
            cursor.execute(command)
            self.connection.commit()

    async def select(self, command: str):

        with self.connection.cursor() as cursor:
            cursor.execute(command)
            return cursor.fetchall()