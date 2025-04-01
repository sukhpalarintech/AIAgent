import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { BsSend, BsRobot, BsPerson } from "react-icons/bs"; // Icons for send, bot, and user

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatContainerRef = useRef(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    const newMessages = [...messages, { sender: "user", text: input }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      // Send API request to Flask backend
      const response = await axios.post("http://localhost:5000/chat",
        {
          message: input,
          user_email: "sukhpal@arintech.in" // Flask expects "user_email"
        },
        {
          headers: {
            "Content-Type": "application/json"
          }
        }
      );

      // Add bot response
      setMessages([...newMessages, { sender: "bot", text: response.data.response }]);
    } catch (error) {
      console.error("Chatbot API Error:", error.response ? error.response.data : error.message);
      setMessages([...newMessages, { sender: "bot", text: "Sorry, something went wrong." }]);
    } finally {
      setLoading(false); // Stop loading indicator
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !loading) {
      sendMessage();
    }
  };

  return (
    <div className="fixed inset-0 flex flex-col bg-gradient-to-br from-blue-50 to-purple-50">
      {/* Chat Header */}
      <div className="flex items-center justify-center p-6 bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg">
        <BsRobot className="text-3xl text-white mr-3" />
        <h1 className="text-2xl font-semibold text-white">HR Chat Assistant</h1>
      </div>

      {/* Chat Messages */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-6 space-y-4 bg-white"
      >
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`flex items-center max-w-md p-4 rounded-xl shadow-sm transform transition-all duration-200 ${
                msg.sender === "user"
                  ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:scale-105"
                  : "bg-gray-100 text-gray-800 hover:scale-105"
              }`}
            >
              {msg.sender === "bot" && <BsRobot className="mr-3 text-blue-500 text-xl" />}
              {msg.sender === "user" && <BsPerson className="mr-3 text-purple-300 text-xl" />}
              <p className="text-lg">{msg.text}</p>
            </div>
          </div>
        ))}

        {/* Loading Indicator with Bubble Dots Animation */}
        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center bg-gray-100 text-gray-700 px-4 py-3 rounded-lg text-lg">
              <div className="bubble-dots">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Field & Send Button */}
      <div className="p-6 bg-white border-t border-gray-200">
        <div className="flex items-center">
          <input
            type="text"
            className="flex-grow p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all duration-200 text-lg"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button
            className="ml-4 p-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:scale-105 transition duration-200 disabled:opacity-50 flex items-center justify-center"
            onClick={sendMessage}
            disabled={loading}
          >
            <BsSend className="h-6 w-6" />
          </button>
        </div>
      </div>

      {/* Custom CSS for Bubble Dots Animation */}
      <style>
        {`
          .bubble-dots {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
          }
          .bubble-dots .dot {
            width: 8px;
            height: 8px;
            background-color: #4a5568; /* Gray color */
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
          }
          .bubble-dots .dot:nth-child(2) {
            animation-delay: 0.2s;
          }
          .bubble-dots .dot:nth-child(3) {
            animation-delay: 0.4s;
          }
          @keyframes bounce {
            0%, 80%, 100% {
              transform: translateY(0);
            }
            40% {
              transform: translateY(-10px);
            }
          }
        `}
      </style>
    </div>
  );
};

export default Chatbot;