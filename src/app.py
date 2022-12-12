import statistics

from corva import Api, Cache, Logger, ScheduledDepthEvent

from src.configuration import SETTINGS


def example_scheduled_depth_app(event: ScheduledDepthEvent, api: Api, cache: Cache):

    # You have access to asset_id, start_time and end_time of the event.
    asset_id = event.asset_id
    log_identifier = event.log_identifier
    top_depth = event.top_depth
    bottom_depth = event.bottom_depth

    # You have to fetch the realtime drilling data for the asset based on start and end time of the event.
    # start_time and end_time are inclusive so the query is structured accordingly to avoid processing duplicate data
    # We are only querying for weight_on_bit field since that is the only field we need. It is nested under data.
    records = api.get_dataset(
        provider="corva",
        dataset=SETTINGS.wits_collection,
        query={
            'asset_id': asset_id,
            'log_identifier': log_identifier,
            'measured_depth': {
                '$gte': top_depth,
                '$lte': bottom_depth,
            },
        },
        sort={'measured_depth': 1},
        limit=500
    )

    Logger.debug(f"{records}")

    record_count = len(records)

    company_id = records[0].get("company_id")
    dep = records[0].get("data.dep")


    # Getting last exported timestamp from redis
    last_exported_measured_depth = int(float(cache.get(key='measured_depth')) or 0)

    # Making sure we are not processing duplicate data
    if bottom_depth <= last_exported_measured_depth:
        Logger.debug(f"Already processed data until {last_exported_measured_depth=}")
        return None

    # Building the required output
    output = {
        "measured_depth": bottom_depth,
        "asset_id": asset_id,
        "company_id": company_id,
        "log_identifier": log_identifier,
        "provider": SETTINGS.provider,
        "collection": SETTINGS.output_collection,
        "data": {"dep": dep},
        "version": SETTINGS.version
    }

    Logger.debug(f"{asset_id=} {company_id=} {output}")

    Logger.debug(f"{asset_id=} {company_id=}")
    Logger.debug(f"{top_depth=} {bottom_depth=} {record_count=}")
    Logger.debug(f"{output=}")

    # if request fails, lambda will be re-invoked. so no exception handling
    api.post(
        f"api/v1/data/{SETTINGS.provider}/{SETTINGS.output_collection}/", data=[output],
    ).raise_for_status()

    # Storing the output timestamp to cache
    cache.set(key='measured_depth', value=output.get("measured_depth"))

    return output