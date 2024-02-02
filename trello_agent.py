import autogen
import logging
import datetime
from autogen.agentchat.groupchat import GroupChat
from trello import TrelloClient
import memories.trello_config as config
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json


config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-turbo-preview"],
    },
)

llm_config = {
                "functions": [
                     {
                        "name": "create_trello_card",
                        "description": "create a card in trello to track our goals and objectives.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "card_name": {
                                    "type": "string",
                                    "description":"the name of the goal we wish to achieve.",
                                },
                                "card_description": {
                                    "type": "string",
                                    "description":"A siccinct yet complete description of the task to perform.",
                                },
                                "list_alias": {
                                    "type": "string",
                                    "description":"the trello list to assist the card to. Permitted values are: immediate_goals, longterm_goals",
                                },
                                "due_date": {
                                    "type": "string",
                                    "description":"the date by which the goal should be completed, in ISO 8601 format.",
                                }
                            },
                            "required": ["card_name", "card_description","list_alias","due_date"],
                        }
                     }
                ],
                "config_list": config_list,
                "timeout": 60,
                "seed": 42}



logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def create_trello_card(card_name, card_description, list_alias, due_date):
    logging.debug("Starting the create_trello_card function")
    
    try:
        logging.debug("Initializing the Trello Client")
        client = TrelloClient(api_key=config.API_KEY, token=config.API_TOKEN)
        board = client.get_board(config.BOARD_ID)
        list_id = config.LIST_IDS.get(list_alias)
        
        if not list_id:
            logging.error("List alias '%s' is not defined in config", list_alias)
            raise ValueError(f"List alias '{list_alias}' is not defined in config")

        logging.debug("Fetching the list: %s", list_id)
        trello_list = board.get_list(list_id)

        logging.debug("Fetching labels for the board")
        labels = board.get_labels()
        selected_labels = [label for label in labels if label.name == config.LABEL_NAME]

        logging.debug("Creating the card on the list: %s", trello_list)
        new_card = trello_list.add_card(name=card_name, desc=card_description, labels=selected_labels, due=due_date)
        
        logging.info("Card created successfully: %s", new_card.id)
        return new_card
    except Exception as e:
        logging.exception("An error occurred while creating the Trello card")
        raise e

assistant = AssistantAgent("assistant", llm_config=llm_config)

third_wheel = AssistantAgent("assistant", llm_config=llm_config)

user_proxy = UserProxyAgent("user_proxy", 
                            system_message="""you are a trello card creator. Please provide the name, description, list_alias, and due_date of the card you wish to create. Reply TERMINATE when the task is done.
                                            The create_trello_card function has 4 arguments: The order of the arguments is important. It must be as follows:
                                            card_name:  the name of the task.
                                            card_description: A siccinct yet complete description of the task to perform. 
                                            list_alias: the name of the list to add the goal to. There is a fixed list of options. Choose from: 'immediate_goals', 'longterm_goals'.
                                            due_date: the date by which the task must be completed. date must be YYYY-MM-DD.
                                            Do not include the name of each argument in the request. A properly formatted request would be: create_trello_card('A goal to achieive', 'this is what I will do and how I will do it', 'immediate_goals', '2024-03-01')""",
                            code_execution_config={"work_dir": "coding", "use_docker": False},
                            function_map={"create_trello_card": create_trello_card}
                            ) # IMPORTANT: set to True to run code in docker, recommended


group_chat = GroupChat(
    agents=[assistant,user_proxy,third_wheel], # Include all agents
    messages=['This group makes great trello cards'],
    max_round=30
)

manager_config = {"config_list": config_list, "seed": None}  # cache_seed is None because we want to observe if there is any communication pattern difference if we reran the group chat.
manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=manager_config,code_execution_config=False)
 

user_proxy.initiate_chat(manager, message="Create a simple trello card to make a sandwich.")