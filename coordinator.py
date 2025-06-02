import os
import sys
import mysql.connector
from dotenv import load_dotenv
from agents import Runner
from rich.console import Console
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ai_agents.process_query_agent import ProcessedData, process_query_agent
from ai_agents.generate_message_agent import generate_message_agent

load_dotenv()
console = Console()


class AiEmailSender:


    def __init__(self, query):
        self.query = query


    async def final_output(self):
        
        processed_data = await self.process_query()

        employee_db_data = await self.employee_data_from_database(
            processed_data.employee_name,
            processed_data.employee_last_name,
            processed_data.employee_phone_number,
            processed_data.employee_work_position
            )
               
        employee_name = employee_db_data[0][1]
        employee_last_name = employee_db_data[0][2]
        employee_phone_number = employee_db_data[0][4]
        employee_work_position = employee_db_data[0][5]
        employee_email = employee_db_data[0][3]
        message_prompt = processed_data.prompt

        console.print("[bold green]Rastas darbuotojas:[/bold green]")
        print(f"{employee_name} {employee_last_name}, {employee_email}, {employee_phone_number}, {employee_work_position}")
        
        confirmation = input("Ar šiam darbuotojui norite siųsti pranešimą? Atsakykite TAIP arba NE\n").lower()
        if confirmation == "taip":
            
            generated_email_message = await self.generate_message(employee_name, message_prompt)

            console.print(f"[bold green]\nSiunčiamas pranešimas[/bold green] {employee_name} {employee_last_name}...\n")
            print(f"{generated_email_message.subject}\n\n{generated_email_message.email_message}")
            try:
                await self.send_email(employee_email, generated_email_message.subject, generated_email_message.email_message)
                console.print(f"[bold green]Laiškas išsiųstas {employee_name} {employee_last_name}[/bold green]")
            except:
                console.print("[bold red]Buvo bandoma išsiųsti laišką, bet nepavyko[/bold red]")
        else:
            console.print("[bold red]Užklausa atšaukta. Paleiskite programą per naują[/bold red]")
            sys.exit()


    async def process_query(self) -> ProcessedData:
        """
        Processes query and fetch employee data and prompt for a message.

        Args:
            query: User's query containing employee data and prompt for a email message.

        Returns:
            ProcessedData object ->
            {
            'employee_name': str | None,
            'employee_last_name': str | None,
            'employee_phone_number': str | None,
            'employee_work_position': str | None,
            'prompt': str | None
            }

            Not found data is set to type None.
        """

        process_query_agent_result = await Runner.run(process_query_agent, input=self.query)

        return process_query_agent_result.final_output
    

    async def employee_data_from_database(self, employee_name, employee_last_name, employee_phone_number, employee_work_position):
        """
        Takes processed query data with employee data and fetch related employee from database.
        If not enought information given, raises Error and exits program.

        Args:
            employee_name: str | None,
            employee_last_name: str | None,
            employee_phone_number: str | None,
            employee_work_position: str | None

        Returns:
            List of tuple: [(... , ...)]
        """

        connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="edvinas",
        database="my_store_db"
        )   

        cursor = connection.cursor()
    
        # Based name and last name: Simas Simonavicius
        if employee_name and employee_last_name:
            print(f"Ieškomas darbuotojas: {employee_name} {employee_last_name} ...\n")

            cursor.execute(f"SELECT * FROM employees WHERE first_name LIKE '{employee_name[:-2]}%' and last_name LIKE '{employee_last_name[:-2]}%'")
            results = cursor.fetchall()

        # Based only last name: Simonavicius
        elif not employee_name and employee_last_name:
            print(f"Ieškomas darbuotojas: {employee_last_name} ...\n")

            cursor.execute(f"SELECT * FROM employees WHERE last_name LIKE '{employee_last_name[:-2]}%'")
            results = cursor.fetchall()

        # Based name and phone number: Simas +370...
        elif employee_name and employee_phone_number:
            print(f"Ieškomas darbuotojas: {employee_name}, kurio telefono numeris {employee_phone_number} ...\n")

            cursor.execute(f"SELECT * FROM employees WHERE first_name LIKE '{employee_name[:-2]}%' and phone_number = '{employee_phone_number}'")
            results = cursor.fetchall()

        # Based only phone number: +370...
        elif not employee_name and employee_phone_number:
            print(f"Ieškomas darbuotojas telefono numeriu: {employee_phone_number} ...\n")

            cursor.execute(f"SELECT * FROM employees WHERE phone_number = '{employee_phone_number}")
            results = cursor.fetchall()

        # Based name and work position: Simas Pakuotojas
        elif employee_name and employee_work_position:
            print(f"Ieškomas darbuotojas: {employee_name}, kuris dirba {employee_work_position} ...\n")

            cursor.execute(f"SELECT * FROM employees WHERE first_name LIKE '{employee_name[:-2]}%' and position LIKE '{employee_work_position[:-3]}%'")
            results = cursor.fetchall()

        # Otherwise raise Error
        else:
            cursor.close()
            connection.close()
            console.print("[bold red]Darbuotojas nerastas. Patikrinkite įvestą informaciją[/bold red]")
            sys.exit()

        cursor.close()
        connection.close()

        return results


    async def generate_message(self, employee_name, message_prompt):
        """
        Generates email message based on given employee_name and message_prompt.

        Args:
            employee_name: str,
            message_prompt: str

        Returns:
            EmailMessage object ->
            {
            'subject': str,
            'email_message': str
            }
        """
        
        query  = f"Employee name: {employee_name}\nPrompt: {message_prompt}"
        generate_message_agent_result = await Runner.run(generate_message_agent, input=query)

        return generate_message_agent_result.final_output


    async def send_email(self, employee_email, email_subject, email_body):

        sender_email = os.getenv("EMAIL")
        sender_password = os.getenv("EMAIL_PASSWORD")

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = employee_email
        message["Subject"] = email_subject

        message.attach(MIMEText(email_body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            try:
                server.starttls()
                server.login(sender_email, sender_password)
                
                server.send_message(message)
                print("Email sent successfully!")
                
            except Exception as e:
                print(f"Error sending email: {e}")

    