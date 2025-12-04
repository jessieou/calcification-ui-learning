
# mammo-ui-train-main

## Calcification GUI 
To run Calcification GUI study demo locally, 
1. environment: install packages listed in `requirements.txt` (ie. via creating a virtual environment -- `python3 -m venv .venv`. To activate, run `source .venv/bin/activate`. Then install `pip install -r requirements.txt`.)
2. run `python learning_app.py`.  This will run the Flask app at http://127.0.0.1:8053/.  

## Change log for March 25
1. build pop-up to notify participant if they were right or wrong, and display the correct pathology if wrong, upon clicking "submit" button for each case. (for learning variant, the participant should be notified after each question if they were right or wrong and what the correct answer was.) DONE
    - check CSV file to compare if answer was correct 
    - consider using an alert, or a toast or confirm dialog 
    -   if correct, send a dismissable success alert "well done!" 
    -   if incorrect, send a red warning alert "incorrect, correct pathology is: x"

2. add question DONE
- What's the BI-RADS final assessment? A. BI-RADS 2 B. BI-RADS 3 C. BI-RADS 4

3. notification of correct or wrong for each question DONE

4. store results/submissions DONE

5. port "next" case logic over from `dashboard_final_5class.py` DONE

6. generate (100?) random login IDs

7. make confidence scroller mandatory as well

## Change log for December 2025 timeline
0. load real data for learning cases DONE

1. duplicate app for testing case (ie. doesn't show feedback) DONE

2. put on top of the left image CC mag and right image ML mag? It's important to label them for trainee. DONE

3. case ID on top instead of order DONE

4. add end screen so cases stop going in a loop DONE

5. separate repo for test (testing_app.py) and learn (learning_app.py)
