#!/usr/bin/env python3
"""
This script allows starting the Wikipedia Philosophy experiment from a specific article.
"""

import sys
import argparse
from wiki_core import WikiCrawler

def main():
    parser = argparse.ArgumentParser(description="Wikipedia Philosophy Path from Specific Article")
    parser.add_argument("article", type=str, help="Title of the Wikipedia article to start from")
    parser.add_argument("-s", "--steps", type=int, default=100, help="Maximum steps to take")
    parser.add_argument("-o", "--output", type=str, default="wiki_specific_graph.png", 
                        help="Output file for graph visualization")
    args = parser.parse_args()
    
    # Normalize article title
    article_title = args.article.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/wiki/{article_title}"
    
    print(f"Starting from article: {args.article}")
    
    # Initialize the crawler
    crawler = WikiCrawler()
    
    # Follow the path
    path, steps, titles = crawler.follow_path(url, args.steps)
    
    # Check if we reached Philosophy
    reached_philosophy = crawler.philosophy_url in path
    
    # Print results
    print("\n=== RESULT ===")
    status = "✓" if reached_philosophy else "✗"
    print(f"[{status}] {args.article} -> Philosophy in {steps} steps")
    
    if reached_philosophy:
        print("\nPath taken:")
        for i, url in enumerate(path):
            title = titles.get(url, crawler.get_title_from_url(url))
            print(f"{i}. {title}")
    else:
        # Find where we got stuck
        if steps >= args.steps:
            print("\nReached maximum number of steps without finding Philosophy.")
        else:
            last_url = path[-1]
            last_title = titles.get(last_url, crawler.get_title_from_url(last_url))
            
            if last_url in path[:-1]:
                # Loop detected
                loop_index = path.index(last_url)
                loop = path[loop_index:]
                loop_titles = [titles.get(u, crawler.get_title_from_url(u)) for u in loop]
                print(f"\nLoop detected! Cycle: {' -> '.join(loop_titles)}")
            else:
                # Dead end
                print(f"\nDead end at article: {last_title}")
    
    # Visualize the graph
    crawler.visualize_graph(args.output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 