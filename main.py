import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from coordinator import AiEmailSender


load_dotenv()
console = Console()


async def main():

    console.print("[bold green]Pateikite el.laiško generavimo užklausą\n")

    query = Prompt.ask("Užklausa")

    await AiEmailSender(query).final_output()


if __name__ == "__main__":
    asyncio.run(main())