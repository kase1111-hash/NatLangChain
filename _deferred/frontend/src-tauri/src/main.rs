// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::api::process::{Command, CommandEvent};
use std::sync::Mutex;

struct BackendState {
    child: Option<tauri::api::process::CommandChild>,
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(BackendState { child: None }))
        .setup(|app| {
            // Spawn the backend sidecar
            let (mut rx, child) = Command::new_sidecar("natlangchain-backend")
                .expect("failed to create sidecar command")
                .spawn()
                .expect("failed to spawn backend sidecar");

            // Store the child process handle
            let state = app.state::<Mutex<BackendState>>();
            state.lock().unwrap().child = Some(child);

            // Handle backend output in a separate thread
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[Backend] {}", line);
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[Backend Error] {}", line);
                        }
                        CommandEvent::Terminated(payload) => {
                            println!("[Backend] Process terminated with code: {:?}", payload.code);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::Destroyed = event.event() {
                // Kill the backend when the window is closed
                if let Some(state) = event.window().try_state::<Mutex<BackendState>>() {
                    if let Some(child) = state.lock().unwrap().child.take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running NatLangChain");
}
