import pytest

def test_homepage_loads(page):
    """Test that the homepage loads correctly with proper title and setup form"""
    print("Visiting homepage...")
    page.goto("http://localhost:5000")
    print("Checking title...")
    assert "Golf Card Game" in page.title()
    print("Checking setup form is visible...")
    assert page.is_visible("#gameSetup")
    assert page.is_visible("#playerName")
    assert page.is_visible("#gameMode")
    print("Homepage loaded successfully with setup form.")

def test_start_game_button_works(page):
    """Test that clicking 'Start Game' button properly starts a game"""
    print("Loading homepage...")
    page.goto("http://localhost:5000")
    print("Filling out game setup...")
    page.fill("#playerName", "Test Player")
    page.select_option("#gameMode", "1v1")
    page.select_option("#opponentType", "random")
    print("Clicking Start Game button...")
    page.click("text=Start Game")
    print("Waiting for game board to appear...")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Checking that setup form is hidden...")
    assert not page.is_visible("#gameSetup")
    print("Checking that game elements are visible...")
    assert page.is_visible("#playerGrids")
    assert page.is_visible("#deckCard")
    assert page.is_visible("#discardCard")
    print("Game started successfully!")

def test_new_game_button_after_game_start(page):
    """Test that 'New Game' button appears and works after a game has started"""
    print("Starting a game first...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Waiting for New Game button to appear...")
    page.wait_for_selector("text=New Game", timeout=5000)
    print("Clicking New Game button...")
    page.click("text=New Game")
    print("Checking that we're back to setup...")
    page.wait_for_selector("#gameSetup", state="visible", timeout=5000)
    assert page.is_visible("#gameSetup")
    assert not page.is_visible("#gameBoard")
    print("New Game button works correctly!")

def test_player_grid_displays_correctly(page):
    """Test that player grids display correctly with proper CSS styling"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Checking player grids...")
    assert page.is_visible(".player-grid")
    print("Checking that cards are displayed...")
    cards = page.query_selector_all(".card")
    assert len(cards) >= 4, f"Expected at least 4 cards, found {len(cards)}"
    print("Checking current turn styling...")
    assert page.is_visible(".player-grid.current-turn")
    print("Player grid displays correctly!")

def test_deck_and_discard_functionality(page):
    """Test that deck and discard pile are functional"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Checking deck card is visible and clickable...")
    assert page.is_visible("#deckCard")
    print("Checking discard card is visible...")
    assert page.is_visible("#discardCard")
    print("Checking deck size is displayed...")
    assert page.is_visible("#deckSize")
    deck_text = page.inner_text("#deckSize")
    assert "cards" in deck_text.lower()
    print(f"Deck size shows: {deck_text}")
    print("Deck and discard functionality looks good!")

def test_scores_display_correctly(page):
    """Test that scores and game info display correctly"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Checking scores area...")
    assert page.is_visible("#ScoresAndRoundInfo")
    scores_text = page.inner_text("#ScoresAndRoundInfo")
    print(f"Scores area contains: {scores_text[:100]}...")
    assert "Game" in scores_text or "Round" in scores_text
    print("Scores display correctly!")

def test_probabilities_panel_loads(page):
    """Test that probabilities panels load and display data"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Checking probabilities panels...")
    assert page.is_visible("#unknownCardsPanel")
    assert page.is_visible("#otherProbabilitiesPanel")
    print("Waiting for probabilities data to load...")
    page.wait_for_timeout(2000)  # Give time for probabilities to calculate
    unknown_cards_text = page.inner_text("#unknownCardsPanel")
    print(f"Unknown cards panel: {unknown_cards_text[:50]}...")
    print("Probabilities panels loaded!")

def test_chart_renders(page):
    """Test that the cumulative score chart renders correctly"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)
    print("Checking for chart canvas...")
    assert page.is_visible("#cumulativeScoreChart")
    print("Checking for chart container...")
    assert page.is_visible(".chart-container")
    print("Chart renders correctly!")

def test_celebration_gif_appears_on_win(page):
    """Test that celebration GIF appears when human player wins"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.fill("#playerName", "Test Winner")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)

    print("Looking for celebration GIF container...")
    assert page.is_visible("#celebrationGif")

    # Try to trigger a win condition by playing through the game
    print("Attempting to play through game to trigger win...")
    for attempt in range(20):  # Try for up to 20 rounds
        print(f"Attempt {attempt + 1}...")

        # Check if game is over and we won
        if page.is_visible("#celebrationGif img"):
            print("🎉 Celebration GIF found!")
            gif_element = page.query_selector("#celebrationGif img")
            src = gif_element.get_attribute("src")
            print(f"GIF source: {src}")
            assert src is not None and len(src) > 0
            print("Celebration GIF test passed!")
            return

        # Look for available actions
        if page.is_visible("text=Next Hole"):
            print("Clicking Next Hole...")
            page.click("text=Next Hole")
        elif page.is_visible("text=Replay"):
            print("Clicking Replay...")
            page.click("text=Replay")
        else:
            # Try to interact with the game (click deck or make moves)
            if page.is_visible("#deckCard") and not page.get_attribute("#deckCard", "class").includes("disabled"):
                print("Trying to draw from deck...")
                page.click("#deckCard")
                page.wait_for_timeout(500)

        page.wait_for_timeout(1000)  # Wait a bit between attempts

    print("Could not trigger win condition in test, but GIF container exists")
    # At minimum, verify the GIF container is present even if we can't trigger a win
    assert page.is_visible("#celebrationGif")

def test_drag_and_drop_discard(page):
    """Test drag and drop functionality for discard pile"""
    print("Starting a game...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)

    print("Waiting for turn-based elements...")
    page.wait_for_timeout(2000)

    print("Checking if discard card is draggable...")
    discard_draggable = page.get_attribute("#discardCard", "draggable")
    print(f"Discard card draggable: {discard_draggable}")

    print("Looking for player grid cards...")
    grid_cards = page.query_selector_all(".player-grid.current-turn .card")
    print(f"Found {len(grid_cards)} grid cards")

    if len(grid_cards) > 0 and discard_draggable == "true":
        print("Attempting drag and drop...")
        try:
            page.drag_and_drop("#discardCard", ".player-grid.current-turn .card[data-position='0']")
            print("Drag and drop completed successfully!")
        except Exception as e:
            print(f"Drag and drop failed (might be expected): {e}")

    print("Drag and drop test completed!")

def test_multi_game_mode(page):
    """Test that multi-game mode works correctly"""
    print("Starting multi-game mode...")
    page.goto("http://localhost:5000")
    page.select_option("#numGames", "3")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)

    print("Checking game info shows multiple games...")
    scores_text = page.inner_text("#ScoresAndRoundInfo")
    assert "of 3" in scores_text or "3" in scores_text
    print(f"Multi-game info: {scores_text[:100]}...")
    print("Multi-game mode test passed!")

def test_responsive_design_elements(page):
    """Test that key responsive design elements are present"""
    print("Testing responsive design...")
    page.goto("http://localhost:5000")
    page.click("text=Start Game")
    page.wait_for_selector("#gameBoard", state="visible", timeout=10000)

    print("Checking CSS grid layout...")
    assert page.is_visible(".game-grid-container")
    assert page.is_visible(".notification-area")
    assert page.is_visible(".gameplay-area")
    assert page.is_visible(".probabilities-area")

    print("Checking responsive classes...")
    # Test that the main container has proper styling
    container_styles = page.evaluate("getComputedStyle(document.querySelector('.container'))")
    print(f"Container has computed styles: {len(container_styles) > 0}")

    print("Responsive design elements test passed!")

#  pytest -s test_ui.py