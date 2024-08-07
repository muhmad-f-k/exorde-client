import logging
import argparse
from typing import AsyncGenerator
from exorde.brain import think
from exorde_data import Item
from types import ModuleType
from exorde.counter import AsyncItemCounter
from typing import Callable
import uuid
from datetime import datetime
import traceback
from exorde.create_error_identifier import create_error_identifier
from exorde.get_module_version import get_module_version
import asyncio

async def choose_module(command_line_arguments, counter, websocket_send):
    intent_id = str(uuid.uuid4())
    await websocket_send(
        {
            "intents": {
                intent_id: {
                    "start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            }
        }
    )
    try:
        module, parameters, domain = await think(
            command_line_arguments, counter, websocket_send, intent_id
        )
        await websocket_send(
            {
                "intents": {
                    intent_id: {
                        "module": module.__name__,
                        "parameters": parameters,
                    },
                },
                "modules": {
                    module.__name__: {
                        "version": get_module_version(module.__name__),
                        "intents": {intent_id: {"parameters": parameters}},
                    }
                },
            }
        )
        iterator = module.query(parameters).__aiter__()
        return (iterator, module, parameters, domain, intent_id)
    except Exception as error:
        await websocket_send({"intents": {intent_id: {"error": str(error)}}})
        logging.exception(f"An error occurred in the brain function")
        raise error

async def consumer(
    iterator, websocket_send, intent_id, counter, module, domain, error_count
):
    try:
        while True:
            await asyncio.sleep(0.1)
            try:
                item = await asyncio.wait_for(iterator.__anext__(), timeout=120)
                if isinstance(item, Item):
                    await websocket_send(
                        {
                            "intents": {
                                intent_id: {
                                    "collections": {
                                        str(uuid.uuid4()): {
                                            "url": str(item.url),
                                            "end": datetime.now().strftime(
                                                "%Y-%m-%d %H:%M:%S"
                                            ),
                                        }
                                    }
                                }
                            }
                        }
                    )
                    await counter.increment(domain)
                    yield item
                else:
                    continue
            except StopAsyncIteration:
                logging.info(f"End of iterator {module.__name__} - StopAsyncIteration")
                break
            except asyncio.TimeoutError:
                logging.info(f"TimeoutError for {module.__name__}, continuing...")
                continue
            except GeneratorExit:
                logging.info(f"GeneratorExit received for {module.__name__}, closing consumer.")
                break
            except Exception as e:
                traceback_list = traceback.format_exception(type(e), e, e.__traceback__)
                error_id = create_error_identifier(traceback_list)
                try:
                    await websocket_send(
                        {
                            "intents": {intent_id: {"errors": {error_id: {}}}},
                            "modules": {module.__name__: {"errors": {error_id: {}}}},
                            "errors": {
                                error_id: {
                                    "traceback": traceback_list,
                                    "module": module.__name__,
                                    "intents": {
                                        intent_id: {
                                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"): {}
                                        }
                                    },
                                }
                            },
                        }
                    )
                except Exception as websocket_error:
                    logging.error(f"Failed to send error to websocket: {websocket_error}")

                logging.exception(f"An error occurred retrieving an item using {module}: {e}")
                if domain not in error_count:
                    error_count[domain] = 0
                error_count[domain] += 1
                continue
    except GeneratorExit:
        logging.info(f"GeneratorExit received for {module.__name__}, closing consumer.")
    except Exception as e:
        logging.exception(f"Unexpected exception in consumer: {e}")

async def get_item(
    command_line_arguments: argparse.Namespace,
    counter: AsyncItemCounter,
    websocket_send: Callable,
) -> AsyncGenerator[Item, None]:
    module: ModuleType
    error_count: dict[ModuleType, int] = {}
    while True:
        iterator, module, __parameters__, domain, intent_id = await choose_module(
            command_line_arguments, counter, websocket_send
        )
        try:
            async for item in consumer(
                iterator, websocket_send, intent_id, counter, module, domain, error_count
            ):
                yield item
        except Exception as e:
            logging.exception("Exception occurred in get_item")


