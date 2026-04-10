import structlog


async def main(user_id: int):
    logger.debug("Получение вк клиента и longpoll'а...", user_id=user_id)
    vk_client, vk_longpoll = await get_client_and_longpoll(user_id)
    api = vk_client.get_api()

    tg_client = MyTelegram(user_id, "VkAPI2TgBot")
    logger.debug("Бот стартует...", user_id=user_id)
    await tg_client.init()

    await vk_longpoll.update_longpoll_server(update_ts=True)
    server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts
    logger.info("On server", ts=server_ts, pts=server_pts, user_id=user_id)
    server_ts = server_ts if isinstance(server_ts, int) else 32

    await load_longpoll_info(user_id, vk_longpoll)
    logger.info(
        "Saved", ts=vk_longpoll.ts, pts=vk_longpoll.pts, user_id=user_id
    )
    # if server_ts <
    logger.info(
        f"Bot is getting last {server_pts - (vk_longpoll.pts if isinstance(vk_longpoll.pts, int) else 32)} events",
        user_id=user_id,
    )
    await get_old_messages(api, vk_longpoll, tg_client)

    server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts
    await set_polling_state(user_id, True)
    await tg_client.send_text("Бот запущен!")
    logger.info("Бот запущен!", user_id=user_id)

    while await get_polling_state(user_id):
        try:
            index = 0
            events = await vk_longpoll.check()
            for event in events:
                need_to_log = await handle(event, api, tg_client)
                if need_to_log:
                    index += 1
                    logger.debug(
                        "ts+pts",
                        ts=vk_longpoll.ts,
                        pts=vk_longpoll.pts,
                        user_id=user_id,
                        index=index,
                    )

                await asyncio.sleep(0)
            if index:
                await save_longpoll_info(user_id, vk_longpoll, log=False)
                logger.debug(f"Processed {index} updates", user_id=user_id)
                if user_id == OWNER_ID:
                    logger.info(
                        "ts+pts",
                        ts=vk_longpoll.ts,
                        pts=vk_longpoll.pts,
                        user_id=user_id,
                    )

        except KeyboardInterrupt:
            logger.info("set polling state to False")
            await set_polling_state(user_id, False)

        except TIMEOUT_EXCEPTIONS as ex:
            logger.warning("timeout")
            logger.debug(f"timeout, {ex=}")
            await asyncio.sleep(10)

        except Exception as ex:
            trace = traceback.format_exc()

            public_trace = f"Возникла ошибка. {ex}"
            private_trace = f"{user_id=}, traceback: {trace}"

            logger.warning("Exception!", ex=ex, user_id=user_id)
            print(private_trace)
            logger.debug(private_trace, exc_info=True, user_id=user_id)
            await tg_client.send_text(public_trace)
            await send_to_tg(tg_client, text=private_trace, chat_id=OWNER_ID)

        try:
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            break

    await tg_client.stop()

    await save_longpoll_info(user_id, vk_longpoll, log=True)
    logger.info(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")


logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(__name__)
