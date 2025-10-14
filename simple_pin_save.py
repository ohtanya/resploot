async def save_pins_to_json_simple(channel_name, pins):
    """Save pinned messages to JSON file - simplified version without attachment downloading"""
    try:
        # Create pins data directory if it doesn't exist
        os.makedirs(PINS_DATA_DIR, exist_ok=True)
        
        # Prepare pins data
        pins_data = {
            "channel_name": channel_name,
            "reset_timestamp": datetime.datetime.now().isoformat(),
            "pin_count": len(pins),
            "pins": []
        }
        
        # Extract data from each pin
        for pin in reversed(pins):  # Reverse to keep chronological order
            try:
                # Debug: Print pin information
                print(f"Processing pin {pin.id}")
                print(f"  Content: '{pin.content}' (length: {len(pin.content)})")
                print(f"  Author: {pin.author.display_name}")
                print(f"  Attachments: {len(pin.attachments)}")
                print(f"  Embeds: {len(pin.embeds)}")
                
                pin_data = {
                    "id": pin.id,
                    "author": {
                        "name": pin.author.display_name,
                        "username": str(pin.author),
                        "id": pin.author.id,
                        "avatar_url": str(pin.author.display_avatar.url) if pin.author.display_avatar else None
                    },
                    "content": pin.content,
                    "created_at": pin.created_at.isoformat(),
                    "jump_url": pin.jump_url,
                    "attachments": [
                        {
                            "filename": att.filename,
                            "url": att.url,
                            "original_url": att.url,
                            "size": att.size,
                            "content_type": att.content_type,
                            "downloaded": False
                        }
                        for att in pin.attachments
                    ],
                    "embeds": [embed.to_dict() for embed in pin.embeds] if pin.embeds else [],
                    "reactions": [
                        {
                            "emoji": str(reaction.emoji),
                            "count": reaction.count
                        }
                        for reaction in pin.reactions
                    ] if pin.reactions else []
                }
                pins_data["pins"].append(pin_data)
            except Exception as e:
                print(f"Error processing pin {pin.id}: {e}")
        
        # Save to file with timestamp in filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{channel_name}_{timestamp}.json"
        filepath = os.path.join(PINS_DATA_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(pins_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(pins)} pins to {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Error saving pins to JSON: {e}")
        return None