#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import networkx as nx
import matplotlib.pyplot as plt
import os
from urllib.parse import urljoin, urlparse, unquote
import argparse
from collections import defaultdict

class WikiCrawler:
    def __init__(self):
        self.base_url = "https://en.wikipedia.org"
        self.philosophy_url = "https://en.wikipedia.org/wiki/Philosophy"
        self.visited = {}  # url -> steps to reach it
        self.paths = defaultdict(list)  # url -> path to reach it
        self.graph = nx.DiGraph()
        self.session = requests.Session()
        
        # Add a proper user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'WikiPhilosophyCrawler/1.0 (Educational research project)'
        })
    
    def get_random_article(self):
        """Get a random Wikipedia article URL."""
        random_url = "https://en.wikipedia.org/wiki/Special:Random"
        response = self.session.get(random_url, allow_redirects=True)
        return response.url
    
    def is_valid_wiki_link(self, href):
        """Check if a link is a valid Wikipedia article link."""
        if not href.startswith('/wiki/'):
            return False
        
        # Skip non-article namespaces
        if ':' in href:
            namespaces = ['File:', 'Wikipedia:', 'Help:', 'Template:', 
                          'Category:', 'Portal:', 'Talk:', 'Special:']
            for namespace in namespaces:
                if namespace in href:
                    return False
        
        # Skip other non-article pages
        if any(x in href for x in ['#', '(disambiguation)']):
            return False
            
        return True
    
    def remove_parentheses(self, html_text):
        """Remove content within parentheses to find the proper first link."""
        # This is a simplified approach - for a more robust solution, we would need
        # to parse the HTML structure properly
        
        # Replace HTML entities
        text = html_text.replace('&lt;', '<').replace('&gt;', '>')
        
        # Track parentheses depth
        result = ""
        depth = 0
        i = 0
        
        while i < len(text):
            if text[i] == '(' and (i == 0 or text[i-1] != '\\'):
                depth += 1
            elif text[i] == ')' and (i == 0 or text[i-1] != '\\'):
                if depth > 0:
                    depth -= 1
            elif depth == 0:
                result += text[i]
            i += 1
                
        return result
    
    def extract_first_link(self, url):
        """Extract the first link from the main text of a Wikipedia article."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.session.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get the title for display
                title_element = soup.find('h1', id='firstHeading')
                if title_element:
                    title = title_element.text
                else:
                    # If we can't find the title element, extract it from the URL
                    title = self.get_title_from_url(url)
                    print(f"Title element not found, using URL-derived title: {title}")
                
                # Find the main content div
                content_div = soup.find('div', {'id': 'mw-content-text'})
                if not content_div:
                    print(f"Warning: Content div not found for {url}, retrying...")
                    retry_count += 1
                    time.sleep(1)
                    continue
                    
                # Print the title we're processing for debugging
                print(f"Processing article: {title}")
                
                # Find paragraphs in the main content
                paragraphs = content_div.select('div.mw-parser-output > p')
                
                if not paragraphs:
                    print(f"Warning: No paragraphs found in {title}")
                    paragraphs = content_div.find_all('p', recursive=False)
                    if not paragraphs:
                        paragraphs = content_div.find_all('p')
                        print(f"Found {len(paragraphs)} paragraphs with broader selection")
                
                # Improved link extraction - iterate through paragraphs
                for paragraph in paragraphs:
                    # Skip empty paragraphs
                    if not paragraph.text.strip():
                        continue
                        
                    # Skip paragraphs that are part of infoboxes, sidebars, or other non-main content
                    should_skip = False
                    for parent in paragraph.parents:
                        parent_classes = parent.get('class', [])
                        if any(cls in ['infobox', 'sidebar', 'metadata', 'navbox', 'vertical-navbox', 'hatnote'] 
                              for cls in parent_classes):
                            should_skip = True
                            break
                    
                    if should_skip:
                        continue
                        
                    # Process paragraph for links - we need to handle parentheses properly
                    # First, we'll extract and analyze the actual HTML structure
                    
                    # Find all links in the paragraph
                    all_links = paragraph.find_all('a', href=True)
                    if not all_links:
                        continue
                        
                    # Go through each link and check if it's valid (not in parentheses)
                    for link in all_links:
                        href = link.get('href', '')
                        if not self.is_valid_wiki_link(href):
                            continue
                            
                        # Check if this link is inside parentheses by analyzing HTML context
                        in_parentheses = False
                        current_element = link
                        
                        # Check the text content before this link for opening parentheses
                        prev_text = ""
                        prev_sibling = current_element.previous_sibling
                        while prev_sibling:
                            if hasattr(prev_sibling, 'string') and prev_sibling.string:
                                prev_text = prev_sibling.string + prev_text
                            elif isinstance(prev_sibling, str):
                                prev_text = prev_sibling + prev_text
                            prev_sibling = prev_sibling.previous_sibling
                            
                        # Count parentheses in the text before this link
                        open_count = prev_text.count('(')
                        close_count = prev_text.count(')')
                        
                        # If there are more opening parentheses than closing ones, 
                        # this link is inside parentheses
                        if open_count > close_count:
                            in_parentheses = True
                            continue  # Skip this link as it's inside parentheses
                            
                        # This is a valid link not in parentheses, use it
                        full_url = urljoin(self.base_url, href)
                        link_text = link.text.strip()
                        print(f"Found first valid link: {link_text} -> {href}")
                        return full_url, title
                
                # If we reach here, we couldn't find a valid link in the main paragraphs
                # Try list items as fallback
                print(f"Warning: No valid link found in main paragraphs for {title}, checking lists...")
                
                list_items = content_div.select('div.mw-parser-output > ul > li, div.mw-parser-output > ol > li')
                for item in list_items:
                    links = item.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if self.is_valid_wiki_link(href):
                            full_url = urljoin(self.base_url, href)
                            link_text = link.text.strip()
                            print(f"Found link in list item: {link_text} -> {href}")
                            return full_url, title
                
                # Last resort - try all paragraphs regardless of location
                print(f"Warning: No valid link found in lists for {title}, checking all content...")
                all_paragraphs = content_div.find_all('p')
                for paragraph in all_paragraphs:
                    links = paragraph.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if self.is_valid_wiki_link(href):
                            full_url = urljoin(self.base_url, href)
                            link_text = link.text.strip()
                            print(f"Found fallback link: {link_text} -> {href}")
                            return full_url, title
                
                # If we still can't find a valid link
                print(f"No valid links found in article: {title}")
                return None, title
                
            except Exception as e:
                print(f"Error processing {url}: {e}, attempt {retry_count+1}/{max_retries}")
                retry_count += 1
                time.sleep(2)  # Wait before retrying
        
        # If all retries failed, extract title from URL as last resort
        title = self.get_title_from_url(url)
        print(f"All retries failed for {url}, using URL-derived title: {title}")
        return None, title
    
    def follow_path(self, start_url=None, max_steps=100):
        """Follow links until reaching Philosophy or hitting max_steps."""
        if not start_url:
            start_url = self.get_random_article()
        
        current_url = start_url
        path = [current_url]
        titles = {}
        steps = 0
        
        print(f"Starting from: {current_url}")
        
        while steps < max_steps:
            # First get information about the current page
            # This extracts both the current page title and the next link to follow
            next_url, current_title = self.extract_first_link(current_url)
            titles[current_url] = current_title
            
            # Check if we've reached Philosophy by checking the current page title
            if current_title == "Philosophy":
                print(f"Found Philosophy in {steps} steps!")
                break
            
            # Check if we've already visited this URL in this path (loop detection)
            if current_url in path[:-1]:
                loop_index = path.index(current_url)
                loop = path[loop_index:]
                print(f"Loop detected! Cycle: {' -> '.join([titles.get(u, self.get_title_from_url(u)) for u in loop])}")
                break
            
            # If no link found, we're at a dead end
            if not next_url:
                print(f"Step {steps}: {current_title} -> Dead end!")
                break
            
            # Print the current step
            print(f"Step {steps}: {current_title} -> ", end="")
            
            # Get the title of the next article from the URL (just for display)
            next_title = self.get_title_from_url(next_url)
            print(f"{next_title}")
            
            # Add to graph
            self.graph.add_edge(current_title, next_title)
            
            # Mark as visited
            self.visited[current_url] = steps
            
            # Move to next URL
            current_url = next_url
            path.append(current_url)
            steps += 1
            
            # Add a slight delay to be nice to Wikipedia servers
            time.sleep(0.5)
        
        # Store the path
        self.paths[start_url] = path
        
        return path, steps, titles
    
    def get_title_from_url(self, url):
        """Extract title from a Wikipedia URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path
            title = path.split("/")[-1].replace("_", " ")
            title = unquote(title)  # Handle URL encoding
            return title
        except:
            return url
    
    def run_experiment(self, num_articles=10, max_steps=100):
        """Run the experiment with multiple random articles."""
        results = []
        
        for i in range(num_articles):
            start_url = self.get_random_article()
            path, steps, titles = self.follow_path(start_url, max_steps)
            
            reached_philosophy = self.philosophy_url in path
            
            result = {
                "start_url": start_url,
                "start_title": titles[start_url],
                "steps": steps,
                "reached_philosophy": reached_philosophy,
                "path": path,
                "path_titles": [titles[url] for url in path]
            }
            
            results.append(result)
            print(f"\nArticle {i+1}/{num_articles} complete.\n")
            
            # Add a longer delay between articles
            time.sleep(1)
        
        return results
    
    def visualize_graph(self, save_path="wiki_graph.png"):
        """Visualize the graph of articles and their relationships."""
        if not self.graph.nodes():
            print("No data to visualize. Run an experiment first.")
            return
        
        # Ensure images directory exists
        os.makedirs("images", exist_ok=True)
        
        # Set output path to images directory
        output_path = os.path.join("images", save_path)
        
        plt.figure(figsize=(15, 12))
        
        # Use a hierarchical layout for better visualization
        pos = nx.spring_layout(self.graph, seed=42, k=0.3)
        
        # Highlight the Philosophy node
        node_colors = []
        node_sizes = []
        
        for node in self.graph.nodes():
            if node == "Philosophy":
                node_colors.append("red")
                node_sizes.append(1000)
            else:
                node_colors.append("lightblue")
                node_sizes.append(500)
        
        # Draw nodes
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=node_sizes)
        
        # Draw edges
        nx.draw_networkx_edges(self.graph, pos, edge_color="gray", arrows=True, arrowsize=15)
        
        # Draw labels
        nx.draw_networkx_labels(self.graph, pos, font_size=8)
        
        plt.title("Paths to Philosophy")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        
        print(f"Graph saved to {output_path}")
        
        # Generate statistics about the graph
        print("\n=== GRAPH STATISTICS ===")
        print(f"Number of nodes: {self.graph.number_of_nodes()}")
        print(f"Number of edges: {self.graph.number_of_edges()}")
        
        # Find nodes with highest in-degree (popular destinations)
        in_degrees = sorted([(node, degree) for node, degree in self.graph.in_degree()], 
                           key=lambda x: x[1], reverse=True)
        print("\nTop 5 most common destinations:")
        for node, degree in in_degrees[:5]:
            print(f"- {node}: {degree} incoming paths")

def main():
    parser = argparse.ArgumentParser(description="Wikipedia Philosophy Crawler")
    parser.add_argument("-n", "--num", type=int, default=5, help="Number of random articles to test")
    parser.add_argument("-s", "--steps", type=int, default=100, help="Maximum steps to take for each article")
    parser.add_argument("-o", "--output", type=str, default="wiki_graph.png", help="Output file for graph visualization")
    args = parser.parse_args()
    
    crawler = WikiCrawler()
    results = crawler.run_experiment(args.num, args.steps)
    
    # Print summary
    print("\n=== SUMMARY ===")
    for i, result in enumerate(results):
        status = "✓" if result["reached_philosophy"] else "✗"
        print(f"{i+1}. [{status}] {result['start_title']} -> Philosophy in {result['steps']} steps")
        
        # Print path for successful attempts
        if result["reached_philosophy"]:
            path_str = " -> ".join(result["path_titles"])
            print(f"   Path: {path_str}")
    
    # Calculate statistics
    successful_paths = [r for r in results if r["reached_philosophy"]]
    success_rate = len(successful_paths) / len(results) if results else 0
    avg_steps = sum(r["steps"] for r in successful_paths) / len(successful_paths) if successful_paths else 0
    
    print(f"\nSuccess rate: {success_rate:.2%}")
    print(f"Average steps to Philosophy: {avg_steps:.2f}")
    
    if successful_paths:
        min_path = min(successful_paths, key=lambda r: r["steps"])
        max_path = max(successful_paths, key=lambda r: r["steps"])
        print(f"Shortest path: {min_path['start_title']} -> Philosophy in {min_path['steps']} steps")
        print(f"Longest path: {max_path['start_title']} -> Philosophy in {max_path['steps']} steps")
    
    # Visualize the graph
    crawler.visualize_graph(args.output)

if __name__ == "__main__":
    main() 