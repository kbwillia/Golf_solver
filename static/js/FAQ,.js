import React, { useState } from "react";
import "./FAQ.css";

const faqs = [

    {
        question: "How to use the chatbot?",
        answer: (
          <ul>
            <li>This uses a combo RAG similarity search and LLM SQL filtering for search and can also chat with the context history.</li>
            <li>If the database is searched, it will return "XXXX job result(s) found" with any filters that were triggered from the LLM.</li>
            <li>These triggers will eventually be tuned for each specific column.</li>
            <li>If no SQL filters are hit, the LLM does a vector similarity search on the 25k jobs in database.</li>
          </ul>
        )
      },

  {
    question: "How to search vs ask about context history?",
    answer: <span>The  <b>'search keywords'</b> are <code>['search', 'find', 'look for', 'where is', 'what is', 'how to', 'can you find']</code>
    <br/><br/>
    The <b>context keywords</b> are <code>['from those jobs', 'of those', 'of the jobs', 'from above', 'compare', 'of those', 'which', 'what about', 'can you elaborate', 'how does', 'explain', 'based on that', 'summarize']</code>.<br/><br/>
    If none of those keywords are hit, a function makes a call to the LLM to decide.</span>
  },

  {
    question: "Data info so I can search effectively?",
    answer: (
      <div>
        <div>It's a European dataset with 25,000+ jobs. The metadata columns include: <b>job title</b>, <b>location</b>, <b>category</b>, <b>company name</b>, <b>salary offered</b>, <b>contact_person</b>, <b>contact_phone_number</b> and more.<br/>Here are some common values to search:</div>
        <div style={{marginTop: 12}}><b>location</b></div>
        <table className="faq-table">
          <tbody>
            <tr><td>Europe</td><td>7399</td></tr>
            <tr><td>UK</td><td>6089</td></tr>
            <tr><td>South East</td><td>4932</td></tr>
            <tr><td>London</td><td>3533</td></tr>
            <tr><td>M4 Corridor</td><td>3014</td></tr>
          </tbody>
        </table>
        <div style={{marginTop: 12}}><b>category</b></div>
        <table className="faq-table">
          <tbody>
            <tr><td>Clinical Research</td><td>9351</td></tr>
            <tr><td>Manufacturing & Operations</td><td>8024</td></tr>
            <tr><td>Pharmaceutical, Healthcare and Medical Sales</td><td>7549</td></tr>
            <tr><td>Regulatory Affairs</td><td>3766</td></tr>
            <tr><td>Pharmaceutical Marketing</td><td>3155</td></tr>
          </tbody>
        </table>
        <div style={{marginTop: 12}}><b>salary_offered</b></div>
        <table className="faq-table">
          <tbody>
            <tr><td>Competitive</td><td>4163</td></tr>
            <tr><td>Neg</td><td>4158</td></tr>
            <tr><td>On Application</td><td>1347</td></tr>
            <tr><td>Competitive / On application</td><td>926</td></tr>
          </tbody>
        </table>
        <div style={{marginTop: 12}}><b>job_title</b></div>
        <table className="faq-table">
          <tbody>
            <tr><td>Experienced Medical Writing</td><td>667</td></tr>
            <tr><td>Territory Manager</td><td>547</td></tr>
            <tr><td>Woundcare Clinical Nurse Advisor RGN Medical Trainer + Sales Support</td><td>444</td></tr>
            <tr><td>Senior Medical Writer</td><td>428</td></tr>
            <tr><td>Senior Medical Writing</td><td>397</td></tr>
          </tbody>
        </table>
      </div>
    )
  },
  {
    question: "Example searches?",
    answer: (
      <div className="faq-examples">
        <p>Here are some examples:</p>
        <ul>
          <li>
            Find doctor jobs in Europe
            <ul>
              <li>Which require pharma background?</li>
              <li>Summarize the differences</li>
            </ul>
          </li>
          <li>
            Search for clinical research category jobs in London
            <ul>
              <li>Tell me more about job 3</li>
              <li>How does that compare to the others?</li>
            </ul>
          </li>
          <li>
          Find me a competitive salary medical sales job in Europe at a smaller company

<ul>
              <li>Which one is the smaller company?</li>
              <li>Which one is the highest growth potential?</li>
            </ul>
          </li>
          <li>
            I'm looking for a high ownership position in regulatory affairs. I have 10 years of experience in the field.
          </li>
          <li>
            I'm looking for a role in medical writing that has some travel benefits and is competitive salary.
          </li>
        </ul>
      </div>
    )
  },


  {
    question: "What is the source of the data?",
    answer: <span>The data is real healthcare job data from Emedcareers website. Here is the link: <a href="https://www.kaggle.com/datasets/PromptCloudHQ/healthcare-job-postings-data-from-emedcareers" target="_blank" rel="noopener noreferrer">Kaggle Dataset</a></span>
  },
  {
    question: "Notes and next steps for improvements?",
    answer: (
      <span>
        <ul style={{ paddingLeft: "20px", marginTop: "6px" }}>
        <li style={{ marginBottom: "10px" }}>
            I made this to get better experience with a fullstack project for AI engineering. I could do this a lot quicker with python then what was already set up on the codebase so I think its a good demo and learning experience. Leared a lot!
          </li>          <li style={{ marginBottom: "10px" }}>
            I have the job hit filter pretty strict because when I was testing, too many columns was being hit. Semantic search still picks up even when the filters don't hit.Once we get to know real data better along with like/dislike feedback, we'll be able to tune it better. I can make a chain-of-thought model (reasoning model) as well. Not an easy problem to solve.
          </li>
          <li style={{ marginBottom: "10px" }}>
            Filtration is what's called 'self query' and the LLM is using a structured output to filter the data if it hits a threshold value, which needs to be tuned with more data.
          </li>
          <li style={{ marginBottom: "10px" }}>
            The formatting for the bot response is a bit messy with spacing and will need fixed in the frontend.
          </li>
          <li style={{ marginBottom: "10px" }}>
            Dynamic prompting and prompt chaining is something that would increase the accuracy of the LLM. Currently just have a static prompt RAG and static for Search.
          </li>
          <li style={{ marginBottom: "10px" }}>
            Having each job in its own bubble or being able to pop out to the right side and get full job details would be a great way to gather metrics upon job clicks and more granular feedback.
          </li>

          <li style={{ marginBottom: "10px" }}>
            I'm using Cerebras LLM for inference (got it for free!) and it's pretty fast! What's slow is creating the query embeddings for new queries — that's being run on my computer (3-5 seconds). I do have cached query embeddings set up. Retrieval from database isn't too bad.
          </li>
          <li style={{ marginBottom: "10px" }}>
            Streaming the llm response so it looks like is typing will have to be an artificial delay on the frontend becauae I have post processing on the bot reply for cleanliness.
          </li>
        </ul>
      </span>
    )
  },


  // Add more FAQs as needed
];

export default function FAQ({ onToggleMinimize, isMinimized }) {
  const [openArr, setOpenArr] = useState(Array(faqs.length).fill(false));

  const handleToggle = idx => {
    setOpenArr(prev => {
      const newArr = [...prev];
      newArr[idx] = !newArr[idx];
      return newArr;
    });
  };

  return (
    <div className={`faq-sidebar ${isMinimized ? 'minimized' : ''}`} style={{ fontFamily: "'Segoe UI', Arial, sans-serif" }}>
      <div className="faq-header">
        <h2>FAQ</h2>
        <button
          className="minimize-btn"
          onClick={onToggleMinimize}
          aria-label={isMinimized ? "Expand FAQ" : "Minimize FAQ"}
          title={isMinimized ? "Expand FAQ" : "Minimize FAQ"}
        >
          {isMinimized ? "›" : "‹"}
        </button>
      </div>
      {!isMinimized && (
        <>
          {faqs.map((faq, idx) => (
            <div key={idx} className="faq-item">
              <button
                className="faq-question"
                onClick={() => handleToggle(idx)}
                aria-expanded={openArr[idx]}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  margin: 0,
                  fontWeight: "bold",
                  fontSize: "1rem",
                  color: "#1A8C8A",
                  cursor: "pointer",
                  width: "100%",
                  textAlign: "left",
                  fontFamily: "'Segoe UI', Arial, sans-serif"
                }}
              >
                {faq.question}
                <span style={{ float: "right" }}>{openArr[idx] ? "-" : "+"}</span>
              </button>
              {openArr[idx] && (
                <div className="faq-answer" style={{ marginTop: 6, fontFamily: "'Segoe UI', Arial, sans-serif" }}>
                  {faq.answer}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
