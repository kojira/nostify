mod db;
use nostr_sdk::client::blocking::Client;
use nostr_sdk::prelude::*;
use serde::{Deserialize, Serialize};

use std::fs::File;

#[derive(Debug, Serialize, Deserialize)]
struct Config {
    relay_servers: Vec<String>,
}

fn main() -> Result<()> {
    let my_keys: Keys = Keys::generate();

    // Show bech32 public key
    let bech32_pubkey: String = my_keys.public_key().to_bech32()?;
    println!("Bech32 PubKey: {}", bech32_pubkey);

    let file = File::open("../common/config.yml")?;
    let config: Config = serde_yaml::from_reader(file)?;
    let pool = db::connect()?;
    println!("mysql pool connected");

    // Create new client
    let client = Client::new(&my_keys);
    for item in config.relay_servers.iter() {
        client.add_relay(item, None)?;
    }
    println!("add_relay");

    // Connect to relays
    client.connect();
    println!("client.connect");

    let subscription = Filter::new()
        .kinds([nostr_sdk::Kind::Metadata, nostr_sdk::Kind::TextNote].to_vec())
        .since(Timestamp::now());

    client.subscribe(vec![subscription]);
    println!("subscribe");

    // Handle notifications
    client.handle_notifications(|notification| {
        if let RelayPoolNotification::Event(_url, event) = notification {
            // if event.kind == Kind::TextNote {
            {
                let result = db::is_matching_ng_word(&pool, &event.content).unwrap();
                if !result {
                    // println!("New Event: {}", event.as_json());
                    let inserted = db::insert_event(&pool, &event);
                    if event.kind == Kind::TextNote && inserted {
                        let filters = db::get_filters(&pool).unwrap();
                        for filter in filters.iter() {
                            let pubkeys = match &filter.pubkeys {
                                Some(s) => s.split(',').collect(),
                                None => vec![],
                            };
                            let mut match_pub = false;
                            let mut match_keyword = false;
                            let mut add_queue = false;
                            for pubkey in pubkeys.iter() {
                                if event.pubkey.to_string().contains(&*pubkey) {
                                    match_pub = true;
                                    break;
                                }
                            }
                            let keywords = match &filter.keywords {
                                Some(s) => s.split('\n').collect(),
                                None => vec![],
                            };
                            for keyword in keywords.iter() {
                                if event
                                    .content
                                    .to_lowercase()
                                    .contains(&keyword.to_lowercase())
                                {
                                    match_keyword = true;
                                    break;
                                }
                            }
                            if pubkeys.is_empty() && match_keyword {
                                add_queue = true;
                            } else if keywords.is_empty() && match_pub {
                                add_queue = true;
                            } else if pubkeys.len() >= 1
                                && keywords.len() >= 1
                                && match_pub
                                && match_keyword
                            {
                                add_queue = true;
                            }
                            if add_queue {
                                db::insert_notify_queue(
                                    &pool,
                                    &event.id.to_hex(),
                                    filter.target_channel_id,
                                )
                                .ok();
                            }
                        }
                    }
                }
            }
        }

        Ok(())
    })?;

    Ok(())
}
