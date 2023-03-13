use chrono::Utc;
use mysql::{params, prelude::*, Opts, OptsBuilder};
use nostr_sdk::Event;
use r2d2_mysql::{mysql::Error as MysqlError, MySqlConnectionManager};
use serde_json::json;
use std::env;
use std::primitive::str;
use thiserror::Error;

const DATABASE_USER: &str = "MYSQL_USER";
const DATABASE_PASS: &str = "MYSQL_PASSWORD";
const DATABASE_NAME: &str = "MYSQL_DATABASE";

const DATABASE_POOL_SIZE: u32 = 4;

fn env_var(name: &str, def_var: Option<String>) -> String {
    let env_var = env::var(name);
    return match def_var {
        Some(v) => env_var.unwrap_or(v),
        _ => env_var.expect(format!("{} must be set", name).as_str()),
    };
}

pub(crate) fn connect() -> Result<r2d2::Pool<MySqlConnectionManager>, MysqlError> {
    let db_user = env_var(DATABASE_USER, None);
    let db_pass = env_var(DATABASE_PASS, None);
    let db_name = env_var(DATABASE_NAME, None);
    let db_url = format!(
        "mysql://{user}:{pass}@{host}:{port}/{name}",
        user = db_user,
        pass = db_pass,
        host = "db",
        port = "3306",
        name = db_name
    );
    println!("db connect");
    let opts = Opts::from_url(&db_url).unwrap();
    let builder = OptsBuilder::from_opts(opts);
    let manager = MySqlConnectionManager::new(builder);
    println!("db connect2");

    // マルチスレッドでプールからコネクションを取り出すような使い方を想定してArcでラップします
    let pool = r2d2::Pool::builder()
        .max_size(DATABASE_POOL_SIZE)
        .build(manager)
        .unwrap();
    println!("db connect3");
    Ok(pool)
}

pub fn insert_event(pool: &r2d2::Pool<MySqlConnectionManager>, event: &Event) -> bool {
    let pool = pool.clone();
    let mut conn = pool.get().unwrap();
    let event_id = event.id.to_hex();
    let event_created_at = event.created_at.as_u64();
    let received_at = Utc::now().timestamp();
    let status = 0;
    let tags_json = json!(event.tags).to_string();
    let param = params! {
        "status" => status,
        "hex_event_id" => event_id,
        "pubkey" => event.pubkey.to_string(),
        "kind" => event.kind.as_u64(),
        "content" => event.content.to_string(),
        "tags" => tags_json,
        "signature" => event.sig.to_string(),
        "event_created_at" => event_created_at,
        "received_at" => received_at
    };

    conn.exec_drop(
        "INSERT IGNORE INTO events (status, hex_event_id, pubkey, kind, content, tags, signature, event_created_at, received_at)
         VALUES (:status, :hex_event_id, :pubkey, :kind, :content, :tags, :signature, FROM_UNIXTIME(:event_created_at), FROM_UNIXTIME(:received_at))",
         param,
    ).unwrap();

    if conn.affected_rows() > 0 {
        true
    } else {
        false
    }
}

struct NgWord {
    // id: i64,
    // status: i64,
    word: String,
    // created_at: Option<String>,
}

pub fn is_matching_ng_word(
    pool: &r2d2::Pool<MySqlConnectionManager>,
    search_word: &str,
) -> Result<bool, mysql::Error> {
    let ng_words = get_ng_words(pool)?;
    for ng_word in ng_words {
        if search_word.contains(&ng_word.word) {
            return Ok(true);
        }
    }
    Ok(false)
}

fn get_ng_words(pool: &r2d2::Pool<MySqlConnectionManager>) -> Result<Vec<NgWord>, mysql::Error> {
    let pool = pool.clone();
    let mut conn = pool.get().unwrap();
    let ng_words_iter = conn
        .exec_iter(
            "SELECT id, status, word, created_at FROM ng_words WHERE status = 0",
            (),
        )
        .unwrap();
    let ng_words: Vec<NgWord> = ng_words_iter
        .map(|row| {
            let r = row.unwrap();
            NgWord {
                // id: r.get("id").unwrap(),
                // status: r.get("status").unwrap(),
                word: r.get("word").unwrap(),
                // created_at: r.get("created_at").unwrap(),
            }
        })
        .collect();
    Ok(ng_words)
}

#[derive(Debug)]
pub struct Filter {
    pub target_channel_id: i64,
    pub pubkeys: Option<String>,
    pub kinds: Option<String>,
    pub authors: Option<String>,
    pub since: Option<i32>,
    pub until: Option<i32>,
    pub event_refs: Option<String>,
    pub pubkey_refs: Option<i32>,
    pub keywords: Option<String>,
}

pub fn get_filters(pool: &r2d2::Pool<MySqlConnectionManager>) -> Result<Vec<Filter>, MysqlError> {
    let pool = pool.clone();
    let mut conn = pool.get().unwrap();
    let filters_iter = conn.exec_iter("SELECT target_channel_id, pubkeys, kinds, authors, since, until, event_refs, pubkey_refs, keywords FROM filters WHERE status = 0",())?;

    let filters: Vec<Filter> = filters_iter
        .map(|row| {
            let r = row.unwrap();
            Filter {
                target_channel_id: r.get("target_channel_id").unwrap(),
                pubkeys: r.get("pubkeys").unwrap(),
                kinds: r.get("kinds").unwrap(),
                authors: r.get("authors").unwrap(),
                since: r.get("since").unwrap(),
                until: r.get("until").unwrap(),
                event_refs: r.get("event_refs").unwrap(),
                pubkey_refs: r.get("pubkey_refs").unwrap(),
                keywords: r.get("keywords").unwrap(),
            }
        })
        .collect();
    Ok(filters)
}

#[derive(Error, Debug)]
pub enum NotifyQueueInsertError {
    #[error("Failed to get a database connection")]
    ConnectionFailed(#[from] r2d2::Error),
    #[error("Failed to insert row into notify_queue table")]
    InsertionFailed(#[from] MysqlError),
}

pub fn insert_notify_queue(
    pool: &r2d2::Pool<MySqlConnectionManager>,
    hex_event_id: &str,
    target_channel_id: i64,
) -> Result<(), NotifyQueueInsertError> {
    let mut conn = pool.get()?;

    let query = "
        INSERT INTO notify_queue (
            hex_event_id,
            status,
            target_channel_id,
            error_count,
            created_at
        ) VALUES (
            :hex_event_id,
            :status,
            :target_channel_id,
            :error_count,
            FROM_UNIXTIME(:created_at)
        )
    ";

    let params = params! {
        "hex_event_id" => hex_event_id,
        "status" => 0,
        "target_channel_id" => target_channel_id,
        "error_count" => 0,
        "created_at" => Utc::now().timestamp(),
    };

    conn.exec_drop(query, params)?;

    Ok(())
}
