import aiosqlite
from loguru import logger
from better_proxy import Proxy
import time

# OopCompanion:suppressRename

class DatabaseManager:
    def __init__(self, db_path: str):

        self.db_path = db_path

    async def create_table(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                node TEXT,
                clientid TEXT,
                nodePassword TEXT,
                idToken TEXT
            );
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS proxy (
                email TEXT UNIQUE,
                proxy TEXT UNIQUE NOT NULL,
                status TEXT
            );
            """)
            await db.commit()
        logger.info("Tables created successfully.")

    async def create_user(self, email: str, password: str, **kwargs):

        async with aiosqlite.connect(self.db_path) as db:
            try:
                kwargs["email"] = email
                kwargs["password"] = password

                columns = ", ".join(kwargs.keys())
                placeholders = ", ".join("?" for _ in kwargs)
                values = tuple(kwargs.values())

                query = f"""
                INSERT INTO users ({columns})
                VALUES ({placeholders});
                """
                await db.execute(query, values)
                await db.commit()
                logger.info(f"User with email {email} created.")
            except aiosqlite.IntegrityError:
                logger.info(f"The user with email {email} already exists.")

    async def create_users_from_file(self, file_path: str):

        try:
            with open(file_path, 'r') as file:
                lines = [line.strip() for line in file if line.strip()]

            if not lines:
                logger.error('File is empty.')
                return

            async with aiosqlite.connect(self.db_path) as db:
                for line in lines:
                    try:
                        if ":" in line:
                            email, password = line.split(":", 1)
                        elif ";" in line:
                            email, password = line.split(";", 1)
                        else:
                            logger.error(f'Invalid line format: {line}')
                            continue

                        await self.create_user(email=email, password=password)
                    except ValueError:
                        logger.error(f'Invalid line format: {line}')
                    except aiosqlite.IntegrityError:
                        logger.info(f"The user with email {email} already exists.")
            logger.info("Users created successfully.")
        except FileNotFoundError:
            logger.error(f"The file {file_path} was not found!")
        except Exception as e:
            logger.error(f"Error: {e}")

    async def find_user(self, identifier: dict, proxy: bool = False) -> bool:

        if not identifier or len(identifier) != 1:
            raise ValueError("Incorrect identifier.")

        key, value = list(identifier.items())[0]
        valid_keys = {"email", "clientId", "proxy"}

        if key not in valid_keys:
            raise ValueError(f"Identifier {key}' invalid")

        table_name = "proxy" if proxy else "users"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(f"SELECT 1 FROM {table_name} WHERE {key} = ? LIMIT 1;", (value,))
            result = await cursor.fetchone()
            await cursor.close()
            return bool(result)

    async def update_user(self, identifier: dict, proxy: bool = False, **kwargs):

        user_exists = await self.find_user(identifier, proxy=proxy)
        if not user_exists:
            key, value = list(identifier.items())[0]
            logger.info(f"User with {key} = {value} not found in {'proxy' if proxy else 'users'} table.")
            return

        key, value = list(identifier.items())[0]
        table_name = "proxy" if proxy else "users"

        async with aiosqlite.connect(self.db_path) as db:
            columns = ", ".join(f"{col} = ?" for col in kwargs)
            values = list(kwargs.values()) + [value]
            query = f"UPDATE {table_name} SET {columns} WHERE {key} = ?;"
            await db.execute(query, values)
            await db.commit()
            logger.info(f"The data for the {'proxy' if proxy else 'user'} with {key} = {value} has been updated.")

    async def get_user_data(self, identifier: dict, proxy: bool = False, *fields):

        user_exists = await self.find_user(identifier, proxy=proxy)
        if not user_exists:
            key, value = list(identifier.items())[0]
            logger.info(f"User with {key} = {value} not found in {'proxy' if proxy else 'users'} table.")
            return None

        columns = ", ".join(fields) if fields else "*"
        key, value = list(identifier.items())[0]
        table_name = "proxy" if proxy else "users"

        async with aiosqlite.connect(self.db_path) as db:
            query = f"SELECT {columns} FROM {table_name} WHERE {key} = ?;"
            cursor = await db.execute(query, (value,))
            row = await cursor.fetchone()
            await cursor.close()

            if not row:
                logger.info(f"User with {key} = {value} not found in {'proxy' if proxy else 'users'} table.")
                return None

            if fields:
                return dict(zip(fields, row))
            else:
                cursor = await db.execute(f"PRAGMA table_info({table_name});")
                column_names = [info[1] for info in await cursor.fetchall()]
                return dict(zip(column_names, row))

    async def delete_user(self, identifier: dict = None, proxy: bool = False):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if identifier is None:
                    logger.error("No identifier.")
                    return

                if "all" in identifier and identifier["all"]:
                    table_name = "proxy" if proxy else "users"
                    await db.execute(f"DELETE FROM {table_name}")
                    await db.commit()
                    logger.error(f"{'Proxies' if proxy else 'Users'} were deleted.")
                    return

                if len(identifier) != 1:
                    logger.error(f"Invalid identifier.")
                    return

                key, value = list(identifier.items())[0]
                user = await self.find_user({key: value}, proxy=proxy)
                if not user:
                    logger.error(f"{'Proxy' if proxy else 'User'} with {key} = {value} not found.")
                    return

                table_name = "proxy" if proxy else "users"
                await db.execute(f"DELETE FROM {table_name} WHERE {key} = ?", (value,))
                await db.commit()
                logger.info(f"{'Proxy' if proxy else 'User'} with {key} = {value} deleted.")
        except Exception as e:
            logger.error(f"Error: {e}")

    async def get_total_points(self, Today: bool = False) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                column = "TotalPoint" if Today else "TodayPoint"
                cursor = await db.execute(f"SELECT SUM({column}) FROM statistics;")
                result = await cursor.fetchone()
                await cursor.close()

                return result[0] if result and result[0] is not None else 0
        except Exception as e:
            logger.error(f"Error: {e}")
            return 0

    async def format_proxy(self, proxy_obj: Proxy) -> str:
        try:
            return f"http://{proxy_obj.login}:{proxy_obj.password}@{proxy_obj.host}:{proxy_obj.port}"
        except Exception as e:
            logger.error(f"Error formatting proxy {proxy_obj}: {e}")
            raise

    async def create_proxies(self, proxies: [str]):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for proxy in proxies:
                    query_check = """
                        SELECT 1 FROM PROXY WHERE proxy = ? LIMIT 1;
                    """
                    result = await db.execute(query_check, (proxy,))
                    existing_proxy = await result.fetchone()

                    if existing_proxy:
                        logger.info(f"Proxy {proxy} already exists in the database.")
                        continue

                    query_insert = """
                       INSERT INTO PROXY (proxy)
                       VALUES (?);
                    """
                    await db.execute(query_insert, (proxy,))
                await db.commit()
                logger.info(f"{len(proxies)} proxies added to the database.")
        except aiosqlite.IntegrityError as e:
            logger.warning(f"Some proxies already exist: {e}")
        except Exception as e:
            logger.error(f"Error adding proxies to the database: {e}")

    async def load_proxies_from_file(self, file_path: str):
        try:
            emails = await self.get_all_emails_from_proxy()

            with open(file_path, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]

            if not proxies:
                logger.error("Proxy file is empty.")
                return

            if len(emails) > len(proxies):
                logger.warning(f"Not enough proxies in the file ({len(proxies)}). "
                               f"Total emails: {len(emails)}. Operation aborted.")
                return

            formatted_proxies = []
            for proxy in proxies:
                proxy = proxy.strip()

                if '@' in proxy:
                    credentials, address = proxy.split('@')
                    host, port = address.split(':')
                    login, password = credentials.split(':')
                else:
                    parts = proxy.split(':')
                    host = parts[0]
                    port = int(parts[1])
                    login = parts[2] if len(parts) > 2 else None
                    password = parts[3] if len(parts) > 3 else None

                proxy_obj = Proxy(host=host, port=port, login=login, password=password)
                formatted_proxy = await self.format_proxy(proxy_obj)
                formatted_proxies.append(formatted_proxy)

            await self.create_proxies(formatted_proxies)

            await self.delete_proxies_not_in_file(formatted_proxies)

            await self.assign_emails_to_null_proxies(emails)

            logger.info("Proxies successfully loaded, cleaned, and assigned emails.")
        except FileNotFoundError:
            logger.error(f"The file '{file_path}' was not found.")
        except Exception as e:
            logger.error(f"Error processing proxies from file: {e}")

    async def get_all_proxies_from_db(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT proxy FROM PROXY;"
                result = await db.execute(query)
                proxies = await result.fetchall()
                return [proxy[0] for proxy in proxies]
        except Exception as e:
            logger.error(f"Error fetching proxies from the database: {e}")
            return []

    async def delete_proxies_not_in_file(self, proxies_from_file: [str]):
        try:
            proxies_from_db = await self.get_all_proxies_from_db()

            proxies_to_delete = [proxy for proxy in proxies_from_db if proxy not in proxies_from_file]

            for proxy in proxies_to_delete:
                await self.delete_user({'proxy': proxy}, True)
                logger.info(f"Deleted proxy {proxy} from the database.")
        except Exception as e:
            logger.error(f"Error deleting proxies from database: {e}")

    async def get_proxies_with_status_none(self, limit: int) -> list:

        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT proxy FROM proxy
                    WHERE status IS NULL
                    LIMIT ?;
                """
                cursor = await db.execute(query, (limit,))
                rows = await cursor.fetchall()
                await cursor.close()

                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error fetching proxies: {e}")
            return []

    async def assign_email_to_nearest_proxy(self, email: str):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query_find_proxy = """
                    SELECT proxy FROM proxy
                    WHERE status IS NULL
                    LIMIT 1;
                """
                cursor = await db.execute(query_find_proxy)
                proxy_record = await cursor.fetchone()
                await cursor.close()

                if not proxy_record:
                    logger.info(f"No available proxy with status 'none' for email {email}.")
                    return

                proxy = proxy_record[0]

                query_update_proxy = """
                    UPDATE proxy
                    SET email = ?, status = 'assigned'
                    WHERE proxy = ?;
                """
                await db.execute(query_update_proxy, (email, proxy))
                await db.commit()

                logger.info(f"Assigned email {email} to proxy {proxy}.")
        except Exception as e:
            logger.error(f"Error assigning email {email} to nearest proxy: {e}")

    async def replace_banned_proxy(self, email: str):
        try:
            current_time = int(time.time())
            future_time = current_time + 20 * 60

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("BEGIN IMMEDIATE;")

                query_get_proxies = """
                    SELECT proxy, 
                           (SELECT proxy FROM proxy WHERE (status IS NULL OR status < ?) AND email IS NULL LIMIT 1) AS new_proxy
                    FROM proxy
                    WHERE email = ?
                    LIMIT 1;
                """
                cursor = await db.execute(query_get_proxies, (current_time, email))
                result = await cursor.fetchone()
                await cursor.close()

                current_proxy = result[0] if result else None
                new_proxy = result[1] if result else None

                if new_proxy:
                    cursor = await db.execute("SELECT email FROM proxy WHERE proxy = ? AND email IS NULL;",
                                              (new_proxy,))
                    check_result = await cursor.fetchone()
                    await cursor.close()

                    if not check_result:
                        logger.info("New proxy was already taken. Aborting.")
                        await db.rollback()
                        return

                    if current_proxy:
                        await db.execute("""
                            UPDATE proxy
                            SET email = NULL, status = ?
                            WHERE proxy = ?;
                        """, (future_time, current_proxy))
                        logger.info(f"Removed email from proxy {current_proxy} and updated status to {future_time}.")

                    await db.execute("""
                        UPDATE proxy
                        SET email = ?, status = 'active'
                        WHERE proxy = ? AND email IS NULL;
                    """, (email, new_proxy))
                    logger.info(f"Assigned proxy {new_proxy} to email {email} with status 'active'.")
                else:
                    logger.info("No available proxy found.")

                await db.commit()

        except Exception as e:
            logger.error(f"Error replacing proxy for email {email}: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")

    async def get_all_emails_from_proxy(self) -> list:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT DISTINCT email FROM proxy WHERE email IS NOT NULL;"
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                await cursor.close()

                emails = [row[0] for row in rows]
                logger.info(f"Fetched {len(emails)} emails from proxy table.")
                return emails
        except Exception as e:
            logger.error(f"Error fetching emails from proxy table: {e}")
            return []

    async def assign_emails_to_null_proxies(self, emails: list):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query_get_null_proxies = """
                    SELECT proxy FROM proxy WHERE email IS NULL LIMIT ?;
                """
                cursor = await db.execute(query_get_null_proxies, (len(emails),))
                proxies = await cursor.fetchall()
                await cursor.close()

                if not proxies:
                    logger.info("No proxies with NULL email found.")
                    return

                if len(proxies) < len(emails):
                    logger.warning("⚠️ The number of available proxies is less than the number of emails!")
                    return

                proxies = [row[0] for row in proxies]
                for proxy, email in zip(proxies, emails):
                    try:
                        query_update_proxy = """
                            UPDATE proxy
                            SET email = ?, status = 'active'
                            WHERE proxy = ? AND email IS NULL;
                        """
                        await db.execute(query_update_proxy, (email, proxy))
                        logger.info(f"Assigned email '{email}' to proxy")
                    except Exception as e:
                        if str(e) == 'UNIQUE constraint failed: proxy.email':
                            logger.info(f"Proxy already has an assigned email. Skipping.")
                        else:
                            logger.error(f"Error assigning email '{email}' to proxy '{proxy}': {e}")

                await db.commit()
                logger.info("Successfully assigned emails to proxies with NULL email.")
        except Exception as e:
            logger.error(f"Error assigning emails to proxies: {e}")

    async def get_all_data(self, email: bool = True, no_idToken: bool = True):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                column = 'email' if email else 'password'

                condition = "idToken IS NULL OR idToken = ''" if no_idToken else "idToken IS NOT NULL AND idToken != ''"

                query = f"""
                    SELECT {column} FROM users
                    WHERE {condition}
                    ORDER BY ROWID ASC;
                """
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                await cursor.close()

                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error fetching data without idToken: {e}")
            return []

    async def get_all_emails_node(self) -> list:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT email FROM users WHERE node IS NOT NULL AND node != '' ORDER BY ROWID ASC;"
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                await cursor.close()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    async def add_statistics_table(self):

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                email TEXT UNIQUE NOT NULL,
                TotalPoint INTEGER DEFAULT 0,
                TodayPoint INTEGER DEFAULT 0,
                Taps INTEGER DEFAULT 0,
                TodayTaps INTEGER DEFAULT 0,
                MimingTime INTEGER DEFAULT 0
            );
            """)
            await db.commit()
        logger.info("Table `statistics` created successfully.")

    async def add_emails_to_statistics(self, emails):
        async with aiosqlite.connect(self.db_path) as db:
            for email in emails:
                try:
                    await db.execute("""
                    INSERT INTO statistics (email)
                    VALUES (?);
                    """, (email,))
                except aiosqlite.IntegrityError:
                    logger.warning(f"Email {email} already exists in the statistics table.")
            await db.commit()
        logger.info("Emails added to statistics successfully.")

    async def update_statistics(self, email, updates):

        if not email:
            logger.error("Email is required to update statistics.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            fields = []
            values = []
            for key in ["TotalPoint", "TodayPoint", "Taps", "TodayTaps", "MimingTime"]:
                if key in updates:
                    fields.append(f"{key} = ?")
                    values.append(updates[key])

            if fields:
                values.append(email)
                query = f"""
                UPDATE statistics
                SET {', '.join(fields)}
                WHERE email = ?;
                """
                try:
                    await db.execute(query, values)
                    await db.commit()
                    logger.info(f"Statistics updated successfully for email: {email}.")
                except Exception as e:
                    logger.error(f"Failed to update statistics for email {email}: {e}")
            else:
                logger.warning(f"No updates provided for email: {email}.")

